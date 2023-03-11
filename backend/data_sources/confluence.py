import concurrent.futures
import logging
import os
from datetime import datetime
from typing import List, Optional, Dict

import html2text
import markdown
from atlassian import Confluence
from bs4 import BeautifulSoup

from data_sources.data_source import DataSource
from data_sources.basic_document import BasicDocument, DocumentType
from docs_queue import IndexingQueue


class ConfluenceDataSource(DataSource):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self._confluence = Confluence(
            url=os.getenv('CONFLUENCE_URL'),
            username=os.getenv('CONFLUENCE_USERNAME'),
            password=os.getenv('CONFLUENCE_PASSWORD')
        )

    def _parse_documents_worker(self, raw_docs: List[Dict]) -> List[BasicDocument]:
        logging.info(f'Parsing {len(raw_docs)} documents')
        html_parser = html2text.HTML2Text()
        html_parser.ignore_links = True

        parsed_docs = []
        for raw_page in raw_docs:
            doc_id = raw_page['id']
            fetched_raw_page = self._confluence.get_page_by_id(doc_id, expand='body.storage,history')

            author = fetched_raw_page['history']['createdBy']['displayName']
            author_image = fetched_raw_page['history']['createdBy']['profilePicture']['path']
            author_image_url = fetched_raw_page['_links']['base'] + author_image
            timestamp = datetime.strptime(fetched_raw_page['history']['createdDate'], "%Y-%m-%dT%H:%M:%S.%fZ")
            html_content = fetched_raw_page['body']['storage']['value']
            text = html_parser.handle(html_content)
            md_text = markdown.markdown(text)
            soup = BeautifulSoup(md_text, features='html.parser')
            plain_text = soup.get_text(separator="\n")
            url = fetched_raw_page['_links']['base'] + fetched_raw_page['_links']['webui']
            parsed_docs.append(BasicDocument(title=fetched_raw_page['title'],
                                             content=plain_text,
                                             author=author,
                                             author_image_url=author_image_url,
                                             timestamp=timestamp,
                                             id=doc_id,
                                             integration_name='confluence',
                                             location=raw_page['space_name'],
                                             url=url,
                                             type=DocumentType.DOCUMENT))

        logging.info(f'Parsed {len(parsed_docs)} documents')
        IndexingQueue.get().feed(docs=parsed_docs)

    def _list_space_docs(self, space: Dict) -> List[Dict]:
        logging.info(f'Getting documents from space {space["name"]} ({space["key"]})')
        start = 0
        limit = 500

        space_docs = []
        while True:
            new_batch = self._confluence.get_all_pages_from_space(space['key'], start=start, limit=limit)
            for doc in new_batch:
                doc['space_name'] = space['name']

            space_docs.extend(new_batch)
            if len(new_batch) < limit:
                break

            start += limit

        logging.info(f'Got {len(space_docs)} documents from space {space["name"]}')
        return space_docs

    def _parse_documents_in_parallel(self, raw_docs: List[Dict]) -> List[BasicDocument]:
        workers = 10
        logging.info(f'Start parsing {len(raw_docs)} documents (with {workers} workers)...')

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []
            for i in range(workers):
                futures.append(executor.submit(self._parse_documents_worker, raw_docs[i::workers]))
            concurrent.futures.wait(futures)

    def _get_all_spaces(self):
        # Sometimes the confluence connection fails, so we retry a few times
        retries = 3
        for i in range(retries):
            try:
                return self._confluence.get_all_spaces()['results']
            except Exception as e:
                logging.error(f'Confluence connection failed: {e}')
                if i == retries - 1:
                    raise e

    def feed_new_documents(self):
        spaces = self._get_all_spaces()
        raw_docs = []
        for space in spaces:
            raw_docs.extend(self._list_space_docs(space))

        self._parse_documents_in_parallel(raw_docs)
