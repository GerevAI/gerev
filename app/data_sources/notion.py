import concurrent.futures
import logging
from typing import Optional, Dict

from notion_client import Client

from data_source_api.basic_document import BasicDocument, DocumentType
from data_source_api.base_data_source import BaseDataSource
from data_source_api.exception import InvalidDataSourceConfig
from docs_queue import IndexingQueue
from pydantic import BaseModel


class NotionConfig(BaseModel):
    secret: str


class NotionDataSource(BaseDataSource):

    @staticmethod
    def _parse_page_content(raw_page_content):
        parsed_page_content = ""
        for block in raw_page_content:
            if block["type"] == "paragraph":
                parsed_page_content += block["paragraph"]["text"][0]["plain_text"] + "\n"
            elif block["type"] == "heading_1":
                parsed_page_content += block["heading_1"]["text"][0]["plain_text"] + "\n"
        return parsed_page_content

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
        except Exception as e:
            raise InvalidDataSourceConfig from e

    def __init__(self, data_source_id: int, config: Optional[Dict] = None):
        super().__init__(data_source_id, config)
        notion_config = NotionConfig(**config)
        self._notion = Client(auth=notion_config.secret)

    def feed_new_documents(self):
        notion_pages = self._notion.search(filter={"property": "object", "value": "page"}).get("results")
        self._parse_pages_in_parallel(notion_pages)

    def _parse_pages_worker(self, raw_pages):
        parsed_docs = []
        for page in raw_pages:
            page_id = page["id"]
            page_name = self._extract_page_name(page)

            raw_page_content = self._notion.blocks.children.list(block_id=page_id).get("results")
            parsed_page_content = self._parse_page_content(raw_page_content)

            author = self._notion.users.retrieve(page["created_by"]["id"])

            parsed_docs.append(BasicDocument(title=page_name['title'],
                                             content=parsed_page_content,
                                             author=author["name"],
                                             author_image_url=author["avatar_url"],
                                             timestamp=page["created_time"],
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
