import datetime
import logging
from typing import Dict, List
import requests
import base64
import urllib.parse
from dataclasses import dataclass

from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication

from data_source_api.base_data_source import BaseDataSource, ConfigField, HTMLInputType
from data_source_api.basic_document import DocumentType, BasicDocument
from data_source_api.exception import InvalidDataSourceConfig
from index_queue import IndexQueue
from pydantic import BaseModel
from parsers.html import html_to_text
from data_source_api.utils import parse_with_workers

logger = logging.getLogger(__name__)

@dataclass
class DevOpsConfig(BaseModel):
    organization_url: str
    access_token: str
    project_name: str
    query_id: str

    def __post_init__(self):
        try:
            self.query_id = self.query_id.strip()
            self.access_token = self.access_token.strip()
            self.project_name = self.project_name.strip()
            self.organization_url = self.organization_url.strip()
        except Exception as e:
            raise ValueError from e

class AzuredevopsDataSource(BaseDataSource):
    @staticmethod
    def get_config_fields() -> List[ConfigField]:
        return [
            ConfigField(label="AzureDevOps organization URL", placeholder="https://dev.azure.com/org", name="organization_url"),
            ConfigField(label="Personal Access Token", name="access_token", type=HTMLInputType.PASSWORD),
            ConfigField(label="Project Name", name="project_name"),
            ConfigField(label="Query ID", name="query_id"),
        ]
    
    @staticmethod
    def validate_config(config: Dict) -> None:
        try:
            devops_config = DevOpsConfig(**config)
            credentials = BasicAuthentication('', devops_config.access_token)
            connection = Connection(base_url=devops_config.organization_url, creds=credentials)
            core_client = connection.clients.get_core_client()
            core_client.get_projects()
        except Exception as e:
            raise InvalidDataSourceConfig from e
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        devops_config = DevOpsConfig(**self._config)
        self._config.organization_url = devops_config.organization_url
        self._config.access_token = devops_config.access_token
        self._config.query_id = devops_config.query_id
        self._config.project_name = devops_config.project_name
        credentials = BasicAuthentication('', self._config.access_token)
        connection = Connection(base_url=self._config.organization_url, creds=credentials)
        self._work_item_tracking_client = connection.clients.get_work_item_tracking_client()

    def _parse_documents_worker(self, raw_docs: List[Dict]):
        logging.info(f'Worker parsing {len(raw_docs)} documents')
        parsed_docs = []
        total_fed = 0
        for item in raw_docs:
            for raw_page in item['comments']:
                create_date = datetime.datetime.strptime(raw_page['createdDate'], "%Y-%m-%dT%H:%M:%S.%fZ")
                if create_date < self._last_index_time:
                    continue
                author = raw_page['createdBy']['displayName']
                workitem_id = raw_page['workItemId']
                title = str(raw_page['workItemId']) + ' - ' + raw_page['createdBy']['displayName']
                html_content = raw_page['text']
                plain_text = html_to_text(html_content)
                author_image_url = raw_page['createdBy']['_links']['avatar']['href']
                url = f"{self._config.organization_url}/{urllib.parse.quote(self._config.project_name)}/_workitems/edit/{raw_page['workItemId']}".strip()

                parsed_docs.append(BasicDocument(
                    id=workitem_id,
                    data_source_id=self._data_source_id,
                    author=author,
                    author_image_url=author_image_url,
                    content=plain_text,
                    type=DocumentType.COMMENT,
                    title=title,
                    timestamp=create_date,
                    location=self._config.project_name,
                    url=url
                ))

                if len(parsed_docs) >= 50:
                    total_fed += len(parsed_docs)
                    IndexQueue.get_instance().put(docs=parsed_docs)
                    parsed_docs = []

        IndexQueue.get_instance().put(docs=parsed_docs)
        total_fed += len(parsed_docs)
        if total_fed > 0:
            logging.info(f'Worker fed {total_fed} documents')


    def _list_work_item_comments(self, work_item_url) -> List[Dict]:
        authorization = str(base64.b64encode(bytes(':'+self._config.access_token, 'ascii')), 'ascii')
        headers = {
            'Accept': 'application/json',
            'Authorization': 'Basic '+authorization
        }
        return requests.get(url=work_item_url + '/comments', headers=headers).json()

    def _feed_new_documents(self) -> None:
        logger.info('Feeding new Azure DevOps Work Items')
        raw_docs = []
        work_item_results = self._work_item_tracking_client.query_by_id(self._config.query_id)
        for work_item in work_item_results.work_items:
            result = self._list_work_item_comments(work_item.url)
            if result['totalCount'] > 0:
                raw_docs.append(result)
        parse_with_workers(self._parse_documents_worker, raw_docs)