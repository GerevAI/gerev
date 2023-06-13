import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List

import requests
from data_source.api.base_data_source import BaseDataSource, BaseDataSourceConfig, ConfigField, HTMLInputType
from data_source.api.basic_document import BasicDocument, DocumentType
from data_source.api.exception import InvalidDataSourceConfig
from queues.index_queue import IndexQueue
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Notion API Status codes https://developers.notion.com/reference/status-codes

HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_CONFLICT = 409
HTTP_TOO_MANY_REQUESTS = 429

# 5xx Server Errors
HTTP_INTERNAL_SERVER_ERROR = 500
HTTP_SERVICE_UNAVAILABLE = 503
HTTP_GATEWAY_TIMEOUT = 504

RETRY_AFTER_STATUS_CODES = frozenset(
    {
        HTTP_TOO_MANY_REQUESTS,
        HTTP_INTERNAL_SERVER_ERROR,
        HTTP_SERVICE_UNAVAILABLE,
        HTTP_GATEWAY_TIMEOUT,
    }
)


def _notion_retry_session(token, retries=10, backoff_factor=2.0, status_forcelist=RETRY_AFTER_STATUS_CODES):
    """Creates a retry session"""
    session = requests.Session()
    retry = Retry(
        total=retries,
        connect=retries,
        read=retries,
        status=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        raise_on_redirect=False,
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter()
    adapter.max_retries = retry
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"Notion-Version": "2022-06-28", "Authorization": f"Bearer {token}"})
    return session


class NotionObject(str, Enum):
    page = "page"
    database = "database"


class NotionClient:
    def __init__(self, token):
        self.api_url = "https://api.notion.com/v1"
        self.session = _notion_retry_session(token)

    def auth_check(self):
        url = f"{self.api_url}/users/me"
        response = self.session.get(url)
        response.raise_for_status()

    def get_user(self, user_id):
        url = f"{self.api_url}/users/{user_id}"
        response = self.session.get(url)
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError:
            return {}

    def list_objects(self, notion_object: NotionObject):
        url = f"{self.api_url}/search"
        filter_data = {
            "filter": {"value": notion_object, "property": "object"},
            "sort": {"direction": "ascending", "timestamp": "last_edited_time"},
        }
        response = self.session.post(url, json=filter_data)
        results = response.json()["results"]
        while response.json()["has_more"] is True:
            response = self.session.post(url, json={"start_cursor": response.json()["next_cursor"], **filter_data})
            results.extend(response.json()["results"])
        return results

    def list_pages(self):
        return self.list_objects(NotionObject.page)

    def list_databases(self):
        return self.list_objects(NotionObject.database)

    def list_blocks(self, block_id: str):
        url = f"{self.api_url}/blocks/{block_id}/children"
        params = {"page_size": 100}
        response = self.session.get(url, params=params)
        if not response.json()["results"]:
            return []
        results = response.json()["results"]
        while response.json()["has_more"] is True:
            response = self.session.get(url, params={"start_cursor": response.json()["next_cursor"], **params})
            results.extend(response.json()["results"])
        return results

    def list_database_pages(self, database_id: str):
        url = f"{self.api_url}/databases/{database_id}/query"
        filter_data = {"page_size": 100}
        response = self.session.post(url, json=filter_data)
        results = response.json()["results"]
        while response.json()["has_more"] is True:
            response = self.session.post(
                url,
                json={"start_cursor": response.json()["next_cursor"], **filter_data},
            )
            results.extend(response.json()["results"])
        return results


class NotionConfig(BaseDataSourceConfig):
    token: str


class NotionDataSource(BaseDataSource):
    @staticmethod
    def get_config_fields() -> List[ConfigField]:
        """
        list of the config fields which should be the same fields as in MagicConfig, for dynamic UI generation
        """
        return [
            ConfigField(
                label="Notion Integration Token",
                name="token",
                placeholder="secret_AZefAeAZqsfDAZE",
                input_type=HTMLInputType.PASSWORD,
            )
        ]

    @staticmethod
    async def validate_config(config: Dict) -> None:
        """
        Validate the configuration and raise an exception if it's invalid,
        You should try to actually connect to the data source and verify that it's working
        """
        try:
            parsed_config = NotionConfig(**config)
            notion_client = NotionClient(token=parsed_config.token)
            notion_client.auth_check()
        except Exception as e:
            raise InvalidDataSourceConfig from e

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        notion_config = NotionConfig(**self._raw_config)
        self._notion_client = NotionClient(
            token=notion_config.token,
        )
        self.data_source_id = "DUMMY_SOURCE_ID"

    def _parse_rich_text(self, rich_text: list):
        return "\n".join([text["plain_text"] for text in rich_text])

    def _parse_content_from_blocks(self, notion_blocks):
        return "\n".join(
            [
                self._parse_rich_text(block[block["type"]]["rich_text"])
                for block in notion_blocks
                if block[block["type"]].get("rich_text")
            ]
        )

    def _parse_title(self, page):
        title_prop = next(prop for prop in page["properties"] if page["properties"][prop]["type"] == "title")
        return self._parse_rich_text(page["properties"][title_prop]["title"])

    def _parse_content_from_page(self, page):
        metadata_list = [
            f"{prop}: {self._parse_rich_text(page['properties'][prop].get('rich_text',''))}"
            for prop in page["properties"]
            if prop != "Name"
        ]
        title = f"{self._parse_title(page)}"
        metadata = "\n".join([f"Title: {title}"] + metadata_list)
        page_blocks = self._notion_client.list_blocks(page["id"])
        blocks_content = self._parse_content_from_blocks(page_blocks)
        author = self._notion_client.get_user(page["created_by"]["id"])
        return {
            "id": page["id"],
            "author": author.get("name", ""),
            "author_image_url": author.get("avatar_url", ""),
            "url": page["url"],
            "title": title,
            "location": title,
            "content": metadata + blocks_content,
            "timestamp": datetime.strptime(page["last_edited_time"], "%Y-%m-%dT%H:%M:%S.%fZ"),
        }

    def _feed_new_documents(self) -> None:
        logger.info("Fetching non database pages ...")
        single_pages = self._notion_client.list_pages()
        logger.info(f"Found {len(single_pages)} non database pages ...")

        logger.info("Fetching databases ...")
        databases = self._notion_client.list_databases()
        logger.info(f"Found {len(databases)} databases ...")

        all_database_pages = []
        for database in databases:
            database_pages = self._notion_client.list_database_pages(database["id"])
            logger.info(f"Found {len(database_pages)} pages to index in database {database['id']} ...")
            all_database_pages.extend(database_pages)

        pages = single_pages + all_database_pages
        logger.info(f"Found {len(pages)} pages in total ...")

        for page in pages:
            last_updated_at = datetime.strptime(page["last_edited_time"], "%Y-%m-%dT%H:%M:%S.%fZ")
            if last_updated_at < self._last_index_time:
                # skipping already indexed pages
                continue
            try:
                page_data = self._parse_content_from_page(page)
                logger.info(f"Indexing page {page_data['id']}")
                document = BasicDocument(
                    data_source_id=self._data_source_id,
                    type=DocumentType.DOCUMENT,
                    **page_data,
                )
                IndexQueue.get_instance().put_single(document)
            except Exception as e:
                logger.error(f"Failed to index page {page['id']}", exc_info=e)
