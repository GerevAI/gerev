import logging
import os
from datetime import datetime
from time import sleep
from typing import List, Dict
from urllib.parse import urljoin

from pydantic import BaseModel
from requests import Session, HTTPError
from requests.auth import AuthBase

from data_source.api.base_data_source import BaseDataSource, ConfigField, HTMLInputType
from data_source.api.basic_document import BasicDocument, DocumentType
from data_source.api.exception import InvalidDataSourceConfig
from parsers.html import html_to_text
from queues.index_queue import IndexQueue

logger = logging.getLogger(__name__)


class BookStackAuth(AuthBase):
    def __init__(self, token_id, token_secret, header_key="Authorization"):
        self.header_key = header_key
        self.token_id = token_id
        self.token_secret = token_secret

    def __call__(self, r):
        r.headers[self.header_key] = f"Token {self.token_id}:{self.token_secret}"
        return r


class BookStack(Session):
    VERIFY_SSL = os.environ.get('BOOKSTACK_VERIFY_SSL') is not None

    def __init__(self, url: str, token_id: str, token_secret: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = url
        self.auth = BookStackAuth(token_id, token_secret)
        self.rate_limit_reach = False

    def request(self, method, url_path, *args, **kwargs):
        while self.rate_limit_reach:
            sleep(1)

        url = urljoin(self.base_url, url_path)
        r = super().request(method, url, verify=BookStack.VERIFY_SSL, *args, **kwargs)

        if r.status_code != 200:
            if r.status_code == 429:
                if not self.rate_limit_reach:
                    logger.info("API rate limit reach, waiting...")
                    self.rate_limit_reach = True
                    sleep(60)
                    self.rate_limit_reach = False
                    logger.info("Done waiting for the API rate limit")
                return self.request(method, url, verify=BookStack.VERIFY_SSL, *args, **kwargs)
            r.raise_for_status()
        return r

    def get_list(self, url: str, count: int = 500, sort: str = None, filters: Dict = None):
        # Add filter[...] to keys, avoiding the insertion of unwanted parameters
        if filters is not None:
            filters = {f"filter[{k}]": v for k, v in filters.items()}
        else:
            filters = {}

        data = []
        records = 0
        total = 1  # Set 1 to enter the loop
        while records < total:
            r = self.get(url, params={"count": count, "offset": records, "sort": sort, **filters},
                         headers={"Content-Type": "application/json"})
            json = r.json()
            data += json.get("data")
            records = len(data)
            total = json.get("total")
        return data

    def get_all_books(self) -> List[Dict]:
        return self.get_list("/api/books", sort="+updated_at")

    def get_all_pages_from_book(self, book) -> List[Dict]:
        pages = self.get_list("/api/pages", sort="+updated_at", filters={"book_id": book["id"]})

        # Add parent book object to each page
        for page in pages:
            page.update({"book": book})

        return pages

    def get_page(self, page_id: int):
        r = self.get(f"/api/pages/{page_id}", headers={"Content-Type": "application/json"})
        return r.json()

    def get_user(self, user_id: int):
        try:
            return self.get(f"/api/users/{user_id}", headers={"Content-Type": "application/json"}).json()
        # If the user lack the privileges to make this call, return None
        except HTTPError:
            return None


class BookStackConfig(BaseModel):
    url: str
    token_id: str
    token_secret: str


class BookstackDataSource(BaseDataSource):
    @staticmethod
    def get_config_fields() -> List[ConfigField]:
        return [
            ConfigField(label="BookStack instance URL", name="url"),
            ConfigField(label="Token ID", name="token_id", input_type=HTMLInputType.PASSWORD),
            ConfigField(label="Token Secret", name="token_secret", input_type=HTMLInputType.PASSWORD)
        ]

    @classmethod
    def get_display_name(cls) -> str:
        return "BookStack"

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
        logger.info("Listing books with BookStack")
        return BookstackDataSource.list_books(book_stack=self._book_stack)

    def _feed_new_documents(self) -> None:
        logger.info("Feeding new documents with BookStack")

        books = self._list_books()
        for book in books:
            self.add_task_to_queue(self._feed_book, book=book)

    def _feed_book(self, book: Dict):
        logger.info(f"Getting documents from book {book['name']} ({book['id']})")
        pages = self._book_stack.get_all_pages_from_book(book)
        for page in pages:
            self.add_task_to_queue(self._feed_page, raw_page=page)

    def _feed_page(self, raw_page: Dict):
        last_modified = datetime.strptime(raw_page["updated_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
        if last_modified < self._last_index_time:
            return

        page_id = raw_page["id"]
        page_content = self._book_stack.get_page(page_id)
        author_name = page_content["created_by"]["name"]

        author_image_url = ""
        author = self._book_stack.get_user(raw_page["created_by"])
        if author:
            author_image_url = author["avatar_url"]

        plain_text = html_to_text(page_content["html"])

        url = urljoin(self._config.get('url'), f"/books/{raw_page['book_slug']}/page/{raw_page['slug']}")

        document = BasicDocument(title=raw_page["name"],
                                 content=plain_text,
                                 author=author_name,
                                 author_image_url=author_image_url,
                                 timestamp=last_modified,
                                 id=page_id,
                                 data_source_id=self._data_source_id,
                                 location=raw_page["book"]["name"],
                                 url=url,
                                 type=DocumentType.DOCUMENT)
        IndexQueue.get_instance().put_single(doc=document)

# if __name__ == "__main__":
#     import os
#     config = {"url": os.environ["BOOKSTACK_URL"], "token_id": os.environ["BOOKSTACK_TOKEN_ID"],
#               "token_secret": os.environ["BOOKSTACK_TOKEN_SECRET"]}
#     book_stack = BookstackDataSource(config=config, data_source_id=0)
#     book_stack._feed_new_documents()
