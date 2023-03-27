import logging
from datetime import datetime
from typing import List, Dict
import os

from atlassian import Confluence
from pydantic import BaseModel
from atlassian.errors import ApiError
from requests import HTTPError
from data_source.api.base_data_source import BaseDataSource, ConfigField, HTMLInputType
from data_source.api.basic_document import BasicDocument, DocumentType
from data_source.api.exception import InvalidDataSourceConfig
from parsers.html import html_to_text
from queues.index_queue import IndexQueue

logger = logging.getLogger(__name__)


class ConfluenceConfig(BaseModel):
    url: str
    token: str


class ConfluenceDataSource(BaseDataSource):

    @staticmethod
    def get_config_fields() -> List[ConfigField]:
        return [
            ConfigField(label="Confluence URL", name="url", placeholder="https://example.confluence.com"),
            ConfigField(label="Personal Access Token", name="token", input_type=HTMLInputType.PASSWORD)
        ]

    @staticmethod
    def list_spaces(confluence: Confluence, start=0) -> List[Dict]:
        # Usually the confluence connection fails, so we retry a few times
        retries = 3
        for i in range(retries):
            try:
                return confluence.get_all_spaces(expand='status', start=start)['results']
            except Exception as e:
                logging.error(f'Confluence connection failed: {e}')
                if i == retries - 1:
                    raise e

    @staticmethod
    def validate_config(config: Dict) -> None:
        try:
            parsed_config = ConfluenceConfig(**config)
            confluence = Confluence(url=parsed_config.url, token=parsed_config.token)
            ConfluenceDataSource.list_spaces(confluence=confluence)
        except Exception as e:
            raise InvalidDataSourceConfig from e

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        confluence_config = ConfluenceConfig(**self._config)
        should_verify_ssl = os.environ.get('CONFLUENCE_VERIFY_SSL') is not None
        self._confluence = Confluence(url=confluence_config.url, token=confluence_config.token,
                                      verify_ssl=should_verify_ssl)

    def _list_spaces(self) -> List[Dict]:
        logger.info('Listing spaces')

        spaces = []
        start = 0
        while True:
            new_spaces = ConfluenceDataSource.list_spaces(confluence=self._confluence, start=start)
            if len(new_spaces) == 0:
                break

            spaces.extend(new_spaces)
            start += len(new_spaces)

        logger.info(f'Found {len(spaces)} spaces')
        return spaces

    def _feed_new_documents(self) -> None:
        logger.info('Feeding new documents with Confluence')
        spaces = self._list_spaces()
        for space in spaces:
            self.add_task_to_queue(self._feed_space_docs, space=space)

    def _feed_space_docs(self, space: Dict) -> List[Dict]:
        logging.info(f'Getting documents from space {space["name"]} ({space["key"]})')
        start = 0
        limit = 200  # limit when expanding the version

        space_docs = []
        while True:
            new_batch = self._confluence.get_all_pages_from_space(space['key'], start=start, limit=limit,
                                                                  expand='version')
            for raw_doc in new_batch:
                raw_doc['space_name'] = space['name']
                self.add_task_to_queue(self._feed_doc, raw_doc=raw_doc)

            if len(new_batch) < limit:
                break

            start += limit

        return space_docs

    def _feed_doc(self, raw_doc: Dict):
        last_modified = datetime.strptime(raw_doc['version']['when'], "%Y-%m-%dT%H:%M:%S.%fZ")

        if last_modified < self._last_index_time:
            return

        doc_id = raw_doc['id']
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
#     confluence._feed_new_documents()
