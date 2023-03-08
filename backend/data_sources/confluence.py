import logging
import os
from datetime import datetime
from typing import List, Optional, Dict
import concurrent.futures

import html2text
import markdown
from atlassian import Confluence
from bs4 import BeautifulSoup

from data_sources.data_source import DataSource
from integrations_api.basic_document import BasicDocument


class ConfluenceDataSource(DataSource):
    def __init__(self, config: Optional[Dict] = None):
        self.config = config
        self._confluence = Confluence(
            url=os.getenv('CONFLUENCE_URL'),
            username=os.getenv('CONFLUENCE_USERNAME'),
            password=os.getenv('CONFLUENCE_PASSWORD')
        )

    def _parse_documents(self, raw_docs: List[Dict]) -> List[BasicDocument]:
        logging.info(f'Parsing {len(raw_docs)} documents')
        html_parser = html2text.HTML2Text()
        html_parser.ignore_links = True

        parsed_docs = []
        for doc in raw_docs:
            doc_id = doc['id']
            raw_doc = self._confluence.get_page_by_id(doc_id, expand='body.storage,history')
            author = raw_doc['history']['createdBy']['displayName']
            timestamp = datetime.strptime(raw_doc['history']['createdDate'], "%Y-%m-%dT%H:%M:%S.%fZ")
            html_content = raw_doc['body']['storage']['value']
            text = html_parser.handle(html_content)
            md_text = markdown.markdown(text)
            soup = BeautifulSoup(md_text, features='html.parser')
            plain_text = soup.get_text(separator="\n")
            parsed_docs.append(BasicDocument(title=doc['title'],
                                             content=plain_text,
                                             author=author,
                                             timestamp=timestamp,
                                             id=doc_id,
                                             integration_name='confluence',
                                             url="doc_url"))

        logging.info(f'Parsed {len(parsed_docs)} documents')
        return parsed_docs

    def get_documents(self) -> List[BasicDocument]:
        spaces = self._confluence.get_all_spaces()['results']
        raw_docs = []
        for space in spaces:
            logging.info(f'Getting documents from space {space["name"]}')
            start = 0
            limit = 500

            space_docs = []
            while True:
                new_batch = self._confluence.get_all_pages_from_space(space['key'], start=start, limit=limit)
                space_docs.extend(new_batch)
                if len(new_batch) < limit:
                    break
                start += limit

            logging.info(f'Got {len(space_docs)} documents from space {space["name"]}')
            raw_docs.extend(space_docs)

        logging.info(f'Got {len(raw_docs)} documents from {len(spaces)} spaces, parsing them now')
        parsed_docs = []
        workers = 15
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []
            for i in range(workers):
                futures.append(executor.submit(self._parse_documents, raw_docs[i::workers]))
            for future in futures:
                parsed_docs.extend(future.result())

        return parsed_docs
