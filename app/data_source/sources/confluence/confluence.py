import logging
import os
import dateutil.parser
from typing import List, Dict

from atlassian import Confluence
from atlassian.errors import ApiError
from requests import HTTPError

from data_source.api.base_data_source import BaseDataSource, ConfigField, HTMLInputType, Location, BaseDataSourceConfig
from data_source.api.basic_document import BasicDocument, DocumentType
from data_source.api.exception import InvalidDataSourceConfig
from parsers.html import html_to_text
from queues.index_queue import IndexQueue

logger = logging.getLogger(__name__)


class ConfluenceConfig(BaseDataSourceConfig):
    url: str
    token: str


class ConfluenceDataSource(BaseDataSource):

    @staticmethod
    def get_config_fields() -> List[ConfigField]:
        return [
            ConfigField(label="Confluence URL", name="url", placeholder="https://example.confluence.com"),
            ConfigField(label="Personal Access Token", name="token", input_type=HTMLInputType.PASSWORD)
        ]

    @classmethod
    def get_display_name(cls) -> str:
        return "Confluence Self-Hosted"

    @staticmethod
    def list_spaces(confluence: Confluence, start=0) -> List[Location]:
        # Usually the confluence connection fails, so we retry a few times
        retries = 3
        for i in range(retries):
            try:
                return [Location(label=space['name'], value=space['key'])
                        for space in confluence.get_all_spaces(expand='status', start=start)['results']]
            except Exception as e:
                logging.error(f'Confluence connection failed: {e}')
                if i == retries - 1:
                    raise e

    @staticmethod
    def list_all_spaces(confluence: Confluence) -> List[Location]:
        logger.info('Listing spaces')

        spaces = []
        start = 0
        while True:
            new_spaces = ConfluenceDataSource.list_spaces(confluence=confluence, start=start)
            if len(new_spaces) == 0:
                break

            spaces.extend(new_spaces)
            start += len(new_spaces)

        logger.info(f'Found {len(spaces)} spaces')
        return spaces

    @staticmethod
    async def validate_config(config: Dict) -> None:
        try:
            client = ConfluenceDataSource.confluence_client_from_config(config)
            ConfluenceDataSource.list_spaces(confluence=client)
        except Exception as e:
            raise InvalidDataSourceConfig from e

    @staticmethod
    def confluence_client_from_config(config: Dict) -> Confluence:
        parsed_config = ConfluenceConfig(**config)
        should_verify_ssl = os.environ.get('CONFLUENCE_VERIFY_SSL') is not None
        return Confluence(url=parsed_config.url, token=parsed_config.token, verify_ssl=should_verify_ssl)

    @staticmethod
    def list_locations(config: Dict) -> List[Location]:
        confluence = ConfluenceDataSource.confluence_client_from_config(config)
        return ConfluenceDataSource.list_all_spaces(confluence=confluence)

    @staticmethod
    def has_prerequisites() -> bool:
        return True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._confluence = ConfluenceDataSource.confluence_client_from_config(self._raw_config)

    def _list_spaces(self) -> List[Location]:
        return ConfluenceDataSource.list_all_spaces(confluence=self._confluence)

    def _feed_new_documents(self) -> None:
        logger.info('Feeding new documents with Confluence')
        spaces = self._config.locations_to_index or self._list_spaces()
        for space in spaces:
            self.add_task_to_queue(self._feed_space_docs, space=space)

    def _feed_space_docs(self, space: Location) -> List[Dict]:
        logging.info(f'Getting documents from space {space.label} ({space.value})')
        start = 0
        limit = 200  # limit when expanding the version

        last_index_time = self._last_index_time.strftime("%Y-%m-%d %H:%M")
        cql_query = f'type = page AND Space = "{space.value}" AND lastModified >= "{last_index_time}" ' \
                    f'ORDER BY lastModified DESC'
        logger.info(f'Querying confluence with CQL: {cql_query}')
        while True:
            new_batch = self._confluence.cql(cql_query, start=start, limit=limit,
                                             expand='version')['results']
            len_new_batch = len(new_batch)
            logger.info(f'Got {len_new_batch} documents from space {space.label} (total {start + len_new_batch})')
            for raw_doc in new_batch:
                raw_doc['space_name'] = space.label
                self.add_task_to_queue(self._feed_doc, raw_doc=raw_doc)

            if len(new_batch) < limit:
                break

            start += limit

    def _feed_doc(self, raw_doc: Dict):
        last_modified = dateutil.parser.parse(raw_doc['lastModified'])
        doc_id = raw_doc['content']['id']
        try:
            fetched_raw_page = self._confluence.get_page_by_id(doc_id, expand='body.storage,history')
        except HTTPError as e:
            logging.warning(
                f'Confluence returned status code {e.response.status_code} for document {doc_id} ({raw_doc["title"]}). skipping.')
            return
        except ApiError as e:
            logging.warning(
                f'unable to access document {doc_id} ({raw_doc["title"]}). reason: "{e.reason}". skipping.')
            return

        author = fetched_raw_page['history']['createdBy']['displayName']
        author_image = fetched_raw_page['history']['createdBy']['profilePicture']['path']
        author_image_url = fetched_raw_page['_links']['base'] + author_image
        html_content = fetched_raw_page['body']['storage']['value']
        plain_text = html_to_text(html_content)

        url = fetched_raw_page['_links']['base'] + fetched_raw_page['_links']['webui']

        doc = BasicDocument(title=fetched_raw_page['title'],
                            content=plain_text,
                            author=author,
                            author_image_url=author_image_url,
                            timestamp=last_modified,
                            id=doc_id,
                            data_source_id=self._data_source_id,
                            location=raw_doc['space_name'],
                            url=url,
                            type=DocumentType.DOCUMENT)
        IndexQueue.get_instance().put_single(doc=doc)

# if __name__ == '__main__':
#     import os
#     config = {"url": os.environ['CONFLUENCE_URL'], "token": os.environ['CONFLUENCE_TOKEN']}
#     confluence = ConfluenceDataSource(config=config, data_source_id=0)
#     spaces = ConfluenceDataSource.list_all_spaces(confluence=confluence._confluence)
#     confluence._feed_space_docs(space=spaces[0])
