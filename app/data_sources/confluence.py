import logging
from datetime import datetime
from typing import List, Dict
import os

from atlassian import Confluence

from data_source_api.basic_document import BasicDocument, DocumentType
from data_source_api.base_data_source import BaseDataSource, ConfigField, HTMLInputType
from data_source_api.exception import InvalidDataSourceConfig
from data_source_api.utils import parse_with_workers
from index_queue import IndexQueue
from parsers.html import html_to_text
from pydantic import BaseModel


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
        raw_docs = []
        for space in spaces:
            raw_docs.extend(self._list_space_docs(space))

        parse_with_workers(self._parse_documents_worker, raw_docs)

    def _parse_documents_worker(self, raw_docs: List[Dict]):
        logging.info(f'Worker parsing {len(raw_docs)} documents')

        parsed_docs = []
        total_fed = 0
        for raw_page in raw_docs:
            last_modified = datetime.strptime(raw_page['version']['when'], "%Y-%m-%dT%H:%M:%S.%fZ")
            if last_modified < self._last_index_time:
                continue

            doc_id = raw_page['id']
            fetched_raw_page = self._confluence.get_page_by_id(doc_id, expand='body.storage,history')

            author = fetched_raw_page['history']['createdBy']['displayName']
            author_image = fetched_raw_page['history']['createdBy']['profilePicture']['path']
            author_image_url = fetched_raw_page['_links']['base'] + author_image
            html_content = fetched_raw_page['body']['storage']['value']
            plain_text = html_to_text(html_content)

            url = fetched_raw_page['_links']['base'] + fetched_raw_page['_links']['webui']

            parsed_docs.append(BasicDocument(title=fetched_raw_page['title'],
                                             content=plain_text,
                                             author=author,
                                             author_image_url=author_image_url,
                                             timestamp=last_modified,
                                             id=doc_id,
                                             data_source_id=self._data_source_id,
                                             location=raw_page['space_name'],
                                             url=url,
                                             type=DocumentType.DOCUMENT))
            if len(parsed_docs) >= 50:
                total_fed += len(parsed_docs)
                IndexQueue.get_instance().put(docs=parsed_docs)
                parsed_docs = []

        IndexQueue.get_instance().put(docs=parsed_docs)
        total_fed += len(parsed_docs)
        if total_fed > 0:
            logging.info(f'Worker fed {total_fed} documents')

    def _list_space_docs(self, space: Dict) -> List[Dict]:
        logging.info(f'Getting documents from space {space["name"]} ({space["key"]})')
        start = 0
        limit = 200  # limit when expanding the version

        space_docs = []
        while True:
            new_batch = self._confluence.get_all_pages_from_space(space['key'], start=start, limit=limit,
                                                                  expand='version')
            for doc in new_batch:
                doc['space_name'] = space['name']

            space_docs.extend(new_batch)
            if len(new_batch) < limit:
                break

            start += limit

        return space_docs


# if __name__ == '__main__':
#     import os
#     config = {"url": os.environ['CONFLUENCE_URL'], "token": os.environ['CONFLUENCE_TOKEN']}
#     confluence = ConfluenceDataSource(config=config, data_source_id=0)
#     confluence._feed_new_documents()
