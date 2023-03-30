import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import requests

from data_source.api.base_data_source import BaseDataSource, ConfigField, HTMLInputType, BaseDataSourceConfig
from data_source.api.basic_document import DocumentType, BasicDocument
from queues.index_queue import IndexQueue

logger = logging.getLogger(__name__)

endpoints = [
    'posts',
    'articles',
]


@dataclass
class StackOverflowPost:
    post_id: int
    post_type: str
    link: str
    body_markdown: str
    score: int
    last_activity_date: int
    creation_date: int
    owner_account_id: Optional[int] = None
    owner_reputation: Optional[int] = None
    owner_user_id: Optional[int] = None
    owner_user_type: Optional[str] = None
    owner_profile_image: Optional[str] = None
    owner_display_name: Optional[str] = None
    owner_link: Optional[str] = None
    title:  Optional[str] = None
    last_edit_date:  Optional[str] = None

class StackOverflowConfig(BaseDataSourceConfig):
    api_key: str
    team_name: str


class StackOverflowDataSource(BaseDataSource):

    @staticmethod
    def get_config_fields() -> List[ConfigField]:
        return [
            ConfigField(label="PAT API Key", name="api_key", type=HTMLInputType.TEXT),
            ConfigField(label="Team Name", name="team_name", type=HTMLInputType.TEXT),
        ]

    @staticmethod
    def validate_config(config: Dict) -> None:
        so_config = StackOverflowConfig(**config)
        StackOverflowDataSource._fetch_posts(so_config.api_key, so_config.team_name, 1, 'posts')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        so_config = StackOverflowConfig(**self._raw_config)
        self._api_key = so_config.api_key
        self._team_name = so_config.team_name

    @staticmethod
    def _fetch_posts(api_key: str, team_name: str, page: int, doc_type: str) -> Dict:
        url = f'https://api.stackoverflowteams.com/2.3/{doc_type}?team={team_name}&filter=!nOedRLbqzB&page={page}'
        response = requests.get(url, headers={'X-API-Access-Token': api_key})
        response.raise_for_status()
        return response.json()

    def _feed_new_documents(self) -> None:
        page = 1
        has_more = True
        for doc_type in endpoints:
            while has_more:
                response = self._fetch_posts(self._api_key, self._team_name, page, doc_type)
                posts = response['items']
                logger.info(f'Fetched {len(posts)} posts from Stack Overflow')
                for post_dict in posts:
                    owner_fields = {}
                    if 'owner' in post_dict:
                        owner_fields = {f"owner_{k}": v for k, v in post_dict.pop('owner').items()}
                    if 'title' not in post_dict:
                        post_dict['title'] = post_dict['link']
                    post = StackOverflowPost(**post_dict, **owner_fields)
                    self.add_task_to_queue(self._feed_post, post=post)
                has_more = response['has_more']
                page += 1

    def _feed_post(self, post: StackOverflowPost) -> None:
        logger.info(f'Feeding post {post.title}')
        post_document = BasicDocument(title=post.title, content=post.body_markdown, author=post.owner_display_name,
                                      timestamp=datetime.fromtimestamp(post.creation_date), id=post.post_id,
                                      data_source_id=self._data_source_id, location=post.link,
                                      url=post.link, author_image_url=post.owner_profile_image,
                                      type=DocumentType.MESSAGE)
        IndexQueue.get_instance().put_single(doc=post_document)

# def test():
#     import os
#     config = {"api_key": os.environ['SO_API_KEY'], "team_name": os.environ['SO_TEAM_NAME']}
#     so = StackOverflowDataSource(config=config, data_source_id=0)
#     so._feed_new_documents()
#
#
# if __name__ == '__main__':
#     test()