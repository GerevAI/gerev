import datetime
import logging
from typing import Dict, List
import requests
from dataclasses import dataclass
import json

from data_source_api.base_data_source import BaseDataSource, ConfigField, HTMLInputType
from data_source_api.basic_document import DocumentType, BasicDocument
from data_source_api.exception import InvalidDataSourceConfig
from index_queue import IndexQueue
from parsers.html import html_to_text
from data_source_api.utils import parse_with_workers

logger = logging.getLogger(__name__)

@dataclass
class TrelloConfig():
    organization_name: str
    api_key: str
    api_token: str

    def __post_init__(self):
        self.organization_name = self.organization_name.lower().replace(' ','')

class TrelloDataSource(BaseDataSource):
    @staticmethod
    def get_config_fields() -> List[ConfigField]:
        return [
            ConfigField(label="Trello Organization Name", name="organization_name", type="text"),
            ConfigField(label="API Key", name="api_key", type=HTMLInputType.PASSWORD),
            ConfigField(label="API Token", name="api_token", type=HTMLInputType.PASSWORD),
        ]
    
    @staticmethod
    def validate_config(config: Dict) -> None:
        try:
            trello_config = TrelloConfig(**config)
            url = f"https://api.trello.com/1/organizations/{trello_config.organization_name}/boards"

            headers = {
                "Accept": "application/json"
            }

            query = {
                'key': trello_config.api_key,
                'token': trello_config.api_token
            }
            response = requests.request("GET", url, headers=headers, params=query)
            if response.status_code != 200:
                raise Exception(f"None 200 status code returned. {response.status_code}")
        except Exception as e:
            raise InvalidDataSourceConfig from e
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._trello_config = TrelloConfig(**self._config)
        self._headers = {
                "Accept": "application/json"
            }
    
    def _fetch_board_name(self, card_id) -> str:
        url = f"https://api.trello.com/1/cards/{card_id}/board"
        query = {
            'key': self._trello_config.api_key,
            'token': self._trello_config.api_token
        }

        response = requests.request(
            "GET",
            url,
            params=query
        )
        return json.loads(response.text)['name']
    
    def _fetch_card_comments(self, card_id) -> List[Dict]:
        url = f"https://api.trello.com/1/cards/{card_id}/actions?filter=commentCard"
        query = {
            'key': self._trello_config.api_key,
            'token': self._trello_config.api_token
        }

        response = requests.request(
            "GET",
            url,
            params=query
        )
        return json.loads(response.text)
    
    def _parse_documents_worker(self, raw_docs: List[Dict]):
        logging.info(f'Worker parsing {len(raw_docs)} documents')
        parsed_docs = []
        total_fed = 0

        for raw_page in raw_docs:
            comments = self._fetch_card_comments(raw_page['id'])
            if len(comments) >= 1:
                for comment in comments:
                    last_modified = datetime.datetime.strptime(comment['date'], "%Y-%m-%dT%H:%M:%S.%fZ")
                    if last_modified < self._last_index_time:
                        continue
            
                    html_content = comment['data']['text']
                    plain_text = html_to_text(html_content)

                    parsed_docs.append(BasicDocument(title=raw_page['name'],
                                                    content=plain_text,
                                                    author=comment['memberCreator']['fullName'],
                                                    author_image_url=comment['memberCreator']['avatarUrl'],
                                                    timestamp=last_modified,
                                                    id=comment['id'],
                                                    data_source_id=self._data_source_id,
                                                    url=raw_page['shortUrl'],
                                                    type=DocumentType.COMMENT,
                                                    location=self._fetch_board_name(raw_page['id'])))
                    if len(parsed_docs) >= 50:
                        total_fed += len(parsed_docs)
                        IndexQueue.get_instance().put(docs=parsed_docs)
                        parsed_docs = []

        IndexQueue.get_instance().put(docs=parsed_docs)
        total_fed += len(parsed_docs)
        if total_fed > 0:
            logging.info(f'Worker fed {total_fed} documents')


    def _list_boards(self) -> List[Dict]:
        url = f"https://api.trello.com/1/organizations/{self._trello_config.organization_name}/boards"

        headers = {
            "Accept": "application/json"
        }

        query = {
            'key': self._trello_config.api_key,
            'token': self._trello_config.api_token
        }
        return json.loads(requests.request("GET", url, headers=headers, params=query).text)
    
    def _feed_new_documents(self) -> None:
        logger.info('Feeding new Trello Cards')
        boards = self._list_boards()
        raw_docs = []
        for i in range(0, len(boards), 1):
            url = f"https://api.trello.com/1/boards/{boards[i]['id']}/cards"
            query = {
                'key': self._trello_config.api_key,
                'token': self._trello_config.api_token
            }
            response = requests.request(
                "GET",
                url,
                params=query
            )
            card_results = json.loads(response.text)
            for card in card_results:
                raw_docs.append(card)
        parse_with_workers(self._parse_documents_worker, raw_docs)
            

            