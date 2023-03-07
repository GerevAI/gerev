from typing import List, Optional, Dict
from datetime import datetime

from atlassian import Confluence
import markdown

from data_sources.data_source import DataSource
from integrations_api.basic_document import BasicDocument
from bs4 import BeautifulSoup
import html2text
import os
import logging


class ConfluenceDataSource(DataSource):
    def __init__(self, config: Optional[Dict] = None):
        self.config = config
        self._confluence = Confluence(
            url=os.getenv('CONFLUENCE_URL'),
            username=os.getenv('CONFLUENCE_USERNAME'),
            password=os.getenv('CONFLUENCE_PASSWORD')
        )

    def get_documents(self) -> List[BasicDocument]:
        html_parser = html2text.HTML2Text()
        html_parser.ignore_links = True

        spaces = self._confluence.get_all_spaces()['results']
        documents = []
        for space in spaces:
            logging.info(f'Getting documents from space {space["name"]}')
            start = 0
            limit = 500
            while space_docs := self._confluence.get_all_pages_from_space(space['key'], start=start, limit=limit):
                logging.info(f'Got {len(space_docs)} documents from space {space["name"]}')
                start += limit
                for doc in space_docs:
                    doc_id = doc['id']
                    raw_doc = self._confluence.get_page_by_id(doc_id, expand='body.storage,history')
                    author = raw_doc['history']['createdBy']['displayName']
                    timestamp = datetime.strptime(raw_doc['history']['createdDate'], "%Y-%m-%dT%H:%M:%S.%fZ")
                    html_content = raw_doc['body']['storage']['value']
                    text = html_parser.handle(html_content)
                    md_text = markdown.markdown(text)
                    soup = BeautifulSoup(md_text, features='html.parser')
                    plain_text = soup.get_text(separator="\n")

                    documents.append(BasicDocument(title=doc['title'],
                                                   content=plain_text,
                                                   author=author,
                                                   timestamp=timestamp,
                                                   id=doc_id,
                                                   integration_name='confluence',
                                                   url="doc_url"))

        return documents
