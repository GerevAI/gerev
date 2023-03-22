import concurrent.futures
import logging
from datetime import datetime
from typing import Dict, List

import notion_client
from notion_client import Client, APIResponseError

from data_source_api.basic_document import BasicDocument, DocumentType
from data_source_api.base_data_source import BaseDataSource, ConfigField, HTMLInputType
from data_source_api.exception import InvalidDataSourceConfig
from indexing_queue import IndexingQueue
from pydantic import BaseModel


class NotionConfig(BaseModel):
    secret: str


class NotionDataSource(BaseDataSource):

    @staticmethod
    def get_config_fields() -> List[ConfigField]:
        return [
            ConfigField(label="Integration token", name="secret", input_type=HTMLInputType.PASSWORD)
        ]

    @staticmethod
    def _extract_page_name(page):
        if "title" in page["properties"]:
            return page["properties"]["title"]["title"][0]["plain_text"]

        return page["properties"]["Name"]["title"][0]["plain_text"]

    @staticmethod
    def validate_config(config: Dict) -> None:
        try:
            parsed_config = NotionConfig(**config)
            notion = Client(auth=parsed_config.secret)
            notion.users.list()
        except Exception as e:
            raise InvalidDataSourceConfig from e

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        notion_config = NotionConfig(**self._config)
        self._notion = Client(auth=notion_config.secret)

    def _feed_new_documents(self):
        notion_pages = self._notion.search(filter={"property": "object", "value": "page"}).get("results")
        self._parse_pages_in_parallel(notion_pages)

    def _parse_pages_worker(self, raw_pages):
        parsed_docs = []
        for page in raw_pages:
            last_modified = datetime.strptime(page["last_edited_time"], "%Y-%m-%dT%H:%M:%S.%fZ")
            if last_modified < self._last_index_time:
                continue

            page_id = page["id"]
            page_name = self._extract_page_name(page)

            parsed_page_content = self._parse_page_content(page_id)
            author = self._notion.users.retrieve(page["created_by"]["id"])

            parsed_docs.append(BasicDocument(title=page_name,
                                             content=parsed_page_content,
                                             author=author["name"],
                                             author_image_url=author["avatar_url"],
                                             timestamp=last_modified,
                                             id=page_id,
                                             data_source_id=self._data_source_id,
                                             location=page['url'],
                                             url=page['url'],
                                             type=DocumentType.DOCUMENT))

            if len(parsed_docs) >= 50:
                IndexingQueue.get().feed(docs=parsed_docs)
                parsed_docs = []

        IndexingQueue.get().feed(docs=parsed_docs)

    def _parse_pages_in_parallel(self, pages):
        workers = 10
        logging.info(f'Start parsing {len(pages)} documents (with {workers} workers)...')

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []
            for i in range(workers):
                futures.append(executor.submit(self._parse_pages_worker, pages[i::workers]))
            concurrent.futures.wait(futures)
            for w in futures:
                e = w.exception()
                if e:
                    logging.exception("Worker failed", exc_info=e)

    def _parse_page_content(self, page_id):
        notion_json = {}
        self._notion_page_parser(page_id,
                                 notion=self._notion, notion_json=notion_json)
        page_plain_text = "\n".join(self._find_keys(notion_json, "plain_text"))
        return page_plain_text

    def _block_parser(self, block: dict, notion: notion_client.client.Client) -> dict:
        if block["has_children"]:
            block["children"] = []
            start_cursor = None
            while True:
                if start_cursor is None:
                    blocks = notion.blocks.children.list(block["id"])
                start_cursor = blocks["next_cursor"]
                block["children"].extend(blocks['results'])
                if start_cursor is None:
                    break

            for child_block in block["children"]:
                self._block_parser(child_block, notion)
        return block

    def _notion_page_parser(self, page_id: str, notion: notion_client.client.Client, notion_json: dict):
        try:
            page = notion.pages.retrieve(page_id)
            page_type = 'page'

        except APIResponseError:
            page = notion.databases.retrieve(page_id)
            page_type = 'database'
            pass

        notion_json[page['id']] = page
        start_cursor = None
        notion_json[page['id']]['blocks'] = []

        while True:
            if start_cursor is None:
                if page_type == 'page':
                    blocks = notion.blocks.children.list(page_id)
                elif page_type == 'database':
                    blocks = notion.databases.query(page_id)
            else:
                if page_type == 'page':
                    blocks = notion.blocks.children.list(page_id,
                                                         start_cursor=start_cursor)
                elif page_type == 'database':
                    blocks = notion.databases.query(page_id,
                                                    start_cursor=start_cursor)

            start_cursor = blocks['next_cursor']
            notion_json[page['id']]['blocks'].extend(blocks['results'])
            if start_cursor is None:
                break
        for i_block, block in enumerate(notion_json[page['id']]['blocks']):
            if page_type == 'page':
                if block["type"] in ['page', 'child_page', 'child_database']:
                    self._notion_page_parser(block['id'], notion, notion_json)
                else:
                    block = self._block_parser(block, notion)
                    notion_json[page['id']]['blocks'][i_block] = block
            elif page_type == 'database':
                block["type"] = "db_entry"
                notion_json[page['id']]['blocks'][i_block] = block
                if block["object"] in ['page', 'child_page', 'child_database']:
                    self._notion_page_parser(block['id'], notion, notion_json)

    def _find_keys(self, dictionary, key_name):
        keys = []
        for key, value in dictionary.items():
            if key == key_name:
                keys.append(value)
            elif isinstance(value, dict):
                keys.extend(self._find_keys(value, key_name))
            elif isinstance(value, list):
                for val in value:
                    keys.extend(self._find_keys(val, key_name))
        return keys
