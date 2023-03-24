import logging
from abc import abstractmethod, ABC
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from data_source_api.exception import InvalidDataSourceConfig
from data_source_api.basic_document import BasicDocument, DocumentType
from data_source_api.base_data_source import BaseDataSource, ConfigField, HTMLInputType
from indexing_queue import IndexingQueue
import re
import json
import base64
import requests
from parsers.html import html_to_text
from pydantic import BaseModel

from db_engine import Session
from schemas import DataSource

#import http.client as http_client
#http_client.HTTPConnection.debuglevel = 1


class ZendeskDataSource(BaseDataSource):

    cached_users={}
    cached_sections={}
    cached_categories={}

    @staticmethod
    def get_config_fields() -> List[ConfigField]:
        """
        Returns a list of fields that are required to configure the data source for UI.
        for example:
        """
        return [
            ConfigField(label="BaseUrl", name="baseurl", type="text", placeholder="https://example.zendesk.com"),
            ConfigField(label="Email", name="email", type="text", placeholder="example@example.com"),
            ConfigField(label="Token", name="token", type="password", placeholder="paste-your-token-here")
        ]
    

    @staticmethod
    def validate_config(config: Dict) -> None:
        """
        Validates the config and raises an exception if it's invalid.
        """
        print("Validating zendesk config")
        print(json.dumps(config))
        auth=base64.b64encode(bytes('{}/token:{}'.format(config['email'], config['token']), 'utf-8')) # bytes
        headers = {'Authorization': 'Basic {}'.format(auth.decode("utf-8"))}
        response=requests.get('{}/api/v2/help_center/en-us/articles'.format(config['baseurl']), headers=headers)
        if response.status_code != 200:
            raise InvalidDataSourceConfig

    @staticmethod
    def _is_valid_message(message: Dict) -> bool:
        return 'client_msg_id' in message

    @classmethod
    def get_display_name(cls) -> str:
        """
        Returns the display name of the data source, change GoogleDriveDataSource to Google Drive.
        """
        pascal_case_source = cls.__name__.replace("DataSource", "")
        words = re.findall('[A-Z][^A-Z]*', pascal_case_source)
        return " ".join(words)

    def auth_headers(self):
        auth=base64.b64encode(bytes('{}/token:{}'.format(self._config['email'], self._config['token']), 'utf-8')) # bytes
        return {'Authorization': 'Basic {}'.format(auth.decode("utf-8"))}
    
    def zendesk_get(self, endpoint):
        return requests.get('{}{}'.format(self._config['baseurl'], endpoint), headers=self.auth_headers())
    
    def zendesk_get_user(self, userid):
        if not userid in self.cached_users:
            user=requests.get(self._config['baseurl']+'/api/v2/users/{}'.format(userid), headers=self.auth_headers())
            parsedUser=json.loads(user.content)
            self.cached_users[userid] = parsedUser['user']
        
        return self.cached_users[userid]
    
    def zendesk_get_section(self, sectionid):
        if not sectionid in self.cached_sections:
            url=self._config['baseurl']+'/api/v2/help_center/sections/{}'.format(sectionid)
            section=requests.get(url, headers=self.auth_headers())
            parsedSection=json.loads(section.content)
            self.cached_sections[sectionid] = parsedSection['section']
        
        return self.cached_sections[sectionid]

    def zendesk_get_category(self, categoryid):
        if not categoryid in self.cached_categories:
            category=requests.get(self._config['baseurl']+'/api/v2/help_center/categories/{}'.format(categoryid), headers=self.auth_headers())
            parsedCategory=json.loads(category.content)
            self.cached_categories[categoryid] = parsedCategory['category']
        
        return self.cached_categories[categoryid]

    def _feed_new_documents(self) -> None:
        """
        Feeds the indexing queue with new documents.
        """
        total_fed = 0
        current_page=1
        while True:
            response=self.zendesk_get('/api/v2/help_center/en-us/articles?page={}'.format(current_page))
            articles=json.loads(response.content)

            parsed_docs = []
            for article in articles['articles']:
                print(article['title'])
                last_modified = datetime.strptime(article['updated_at'], "%Y-%m-%dT%H:%M:%SZ")
                if last_modified < self._last_index_time:
                    continue

                doc_id = article['id']
                plain_text = html_to_text(article['body'])
                author=self.zendesk_get_user(article['author_id'])
                author_image_url = ''
                if 'photo' in author and author['photo'] != None:
                    if 'content_url' in author['photo'] and author['photo']['content_url'] != None:
                        author_image_url = author['photo']['content_url']

                section=self.zendesk_get_section(article['section_id'])
                category=self.zendesk_get_category(section['category_id'])

                parsed_docs.append(BasicDocument(title=article['title'],
                                                content=plain_text,
                                                author=author['name'],
                                                author_image_url=author_image_url,
                                                timestamp=last_modified,
                                                id=doc_id,
                                                data_source_id=self._data_source_id,
                                                location=category['name'],
                                                url=article['html_url'],
                                                type=DocumentType.DOCUMENT))
                
            total_fed += len(parsed_docs)
            IndexingQueue.get().feed(docs=parsed_docs)
            parsed_docs = []
            
            print("page: {}, pagecount: {}, current_page: {}".format(articles['page'], articles['page_count'], current_page))
            if articles['page'] == articles['page_count']:
                break

            current_page+=1    

        

    def __init__(self, config: Dict, data_source_id: int, last_index_time: datetime = None) -> None:
        self._config = config
        self._data_source_id = data_source_id

        if last_index_time is None:
            last_index_time = datetime(2012, 1, 1)
        self._last_index_time = last_index_time

