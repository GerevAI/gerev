import concurrent.futures
import logging
from datetime import datetime
from typing import List, Dict

from data_source_api.basic_document import BasicDocument, DocumentType
from data_source_api.base_data_source import BaseDataSource
from data_source_api.exception import InvalidDataSourceConfig
from indexing_queue import IndexingQueue
from parsers.html import html_to_text
from pydantic import BaseModel
from requests import Session
from requests.auth import AuthBase
from urllib.parse import urljoin
from time import sleep


class BookStackAuth(AuthBase):
    def __init__(self, token_id, token_secret, header_key="Authorization"):
        self.header_key = header_key
        self.token_id = token_id
        self.token_secret = token_secret

    def __call__(self, r):
        r.headers[self.header_key] = f"Token {self.token_id}:{self.token_secret}"
        return r


class BookStack(Session):
    def __init__(self, url: str, token_id: str, token_secret: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = url
        self.auth = BookStackAuth(token_id, token_secret)
        self.rate_limit_reach = False

    def request(self, method, url_path, *args, **kwargs):
        while self.rate_limit_reach:
            sleep(1)

        url = urljoin(self.base_url, url_path)
        r = super().request(method, url, *args, **kwargs)

        if r.status_code != 200:
            if r.status_code == 429:
                if not self.rate_limit_reach:
                    logging.info("API rate limit reach, waiting...")
                    self.rate_limit_reach = True
                    sleep(60)
                    self.rate_limit_reach = False
                    logging.info("Done waiting for the API rate limit")
                return self.request(method, url, *args, **kwargs)
            raise Exception("API Error")
        return r

    def get_books(self, count: int = 500, offset: int = 0):
        r = self.get("/api/books", params={"count": count, "offset": offset, "sort": "+updated_at"},
                     headers={"Content-Type": "application/json"})
        data = r.json().get("data")
        records = len(data)
        if records >= count:
            data += self.get_books(count, offset+records)
        return data

    def get_all_books(self) -> list[dict]:
        offset = 0
        count = 500
        return self.get_books(count, offset)

    def get_pages(self, book, count: int = 500, offset: int = 0):
        r = self.get("/api/pages", params={"count": count, "offset": offset, "sort": "+updated_at",
                                           "filter[book_id]": book["id"]},
                     headers={"Content-Type": "application/json"})
        data = r.json().get("data")

        for page in data:
            page.update({"book": book})

        records = len(data)
        if records >= count:
            data += self.get_pages(count, offset + records)
        return data

    def get_all_pages_from_book(self, book) -> list[dict]:
        offset = 0
        count = 500
        return self.get_pages(book, count, offset)

    def get_page(self, page_id: int):
        r = self.get(f"/api/pages/{page_id}", headers={"Content-Type": "application/json"})
        return r.json()

    def get_user(self, user_id: int):
        r = self.get(f"/api/users/{user_id}", headers={"Content-Type": "application/json"})
        if r.status_code != 200:
            return None
        return r.json()


class BookStackConfig(BaseModel):
    url: str
    token_id: str
    token_secret: str


class BookstackDataSource(BaseDataSource):
    @staticmethod
    def list_books(book_stack: BookStack) -> List[Dict]:
        # Usually the book_stack connection fails, so we retry a few times
        retries = 3
        for i in range(retries):
            try:
                return book_stack.get_all_books()
            except Exception as e:
                logging.error(f"BookStack connection failed: {e}")
                if i == retries - 1:
                    raise e

    @staticmethod
    def validate_config(config: Dict) -> None:
        try:
            parsed_config = BookStackConfig(**config)
            book_stack = BookStack(url=parsed_config.url, token_id=parsed_config.token_id,
                                   token_secret=parsed_config.token_secret)
            BookstackDataSource.list_books(book_stack=book_stack)
        except Exception as e:
            raise InvalidDataSourceConfig from e

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        book_stack_config = BookStackConfig(**self._config)
        self._book_stack = BookStack(url=book_stack_config.url, token_id=book_stack_config.token_id,
                                     token_secret=book_stack_config.token_secret)

    def _list_books(self) -> List[Dict]:
        return BookstackDataSource.list_books(book_stack=self._book_stack)

    def _feed_new_documents(self) -> None:
        books = self._list_books()
        raw_docs = []
        for book in books:
            raw_docs.extend(self._list_book_pages(book))

        self._parse_documents_in_parallel(raw_docs)

    def _parse_documents_worker(self, raw_docs: List[Dict]):
        logging.info(f"Worker parsing {len(raw_docs)} documents")

        parsed_docs = []
        total_fed = 0
        for raw_page in raw_docs:
            last_modified = datetime.strptime(raw_page["updated_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
            if last_modified < self._last_index_time:
                continue

            page_id = raw_page["id"]
            page_content = self._book_stack.get_page(page_id)
            author_name = page_content["created_by"]["name"]

            author_image_url = ""
            author = self._book_stack.get_user(raw_page["created_by"])
            if author:
                author_image_url = author["avatar_url"]

            plain_text = html_to_text(page_content["html"])

            url = f"{self._config.get('url')}/books/{raw_page['book_slug']}/page/{raw_page['slug']}"

            parsed_docs.append(BasicDocument(title=raw_page["name"],
                                             content=plain_text,
                                             author=author_name,
                                             author_image_url=author_image_url,
                                             timestamp=last_modified,
                                             id=page_id,
                                             data_source_id=self._data_source_id,
                                             location=raw_page["book"]["name"],
                                             url=url,
                                             type=DocumentType.DOCUMENT))
            if len(parsed_docs) >= 50:
                total_fed += len(parsed_docs)
                IndexingQueue.get().feed(docs=parsed_docs)
                parsed_docs = []

        IndexingQueue.get().feed(docs=parsed_docs)
        total_fed += len(parsed_docs)
        if total_fed > 0:
            logging.info(f"Worker fed {total_fed} documents")

    def _list_book_pages(self, book: Dict) -> List[Dict]:
        logging.info(f"Getting documents from book {book['name']} ({book['id']})")
        return self._book_stack.get_all_pages_from_book(book)

    def _parse_documents_in_parallel(self, raw_docs: List[Dict]):
        workers = 10
        logging.info(f"Parsing {len(raw_docs)} documents (with {workers} workers)...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []
            for i in range(workers):
                futures.append(executor.submit(self._parse_documents_worker, raw_docs[i::workers]))
            concurrent.futures.wait(futures)


if __name__ == "__main__":
    import os
    config = {"url": os.environ["BOOKSTACK_URL"], "token_id": os.environ["BOOKSTACK_TOKEN_ID"], "token_secret": os.environ["BOOKSTACK_TOKEN_SECRET"]}
    book_stack = BookstackDataSource(config=config, data_source_id=0)
    book_stack._feed_new_documents()
