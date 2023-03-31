import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import requests

from data_source.api.base_data_source import BaseDataSource, ConfigField, HTMLInputType, BaseDataSourceConfig
from data_source.api.basic_document import DocumentType, BasicDocument
from queues.index_queue import IndexQueue

from data_source.api.utils import rate_limit

logger = logging.getLogger(__name__)


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
    tags: Optional[List[str]] = None
    view_count: Optional[int] = None

class StackOverflowConfig(BaseDataSourceConfig):
    api_key: str
    team_name: str


@rate_limit(allowed_per_second=15)
def rate_limited_get(url, headers):
    '''
    https://api.stackoverflowteams.com/docs/throttle
    https://api.stackexchange.com/docs/throttle
    Every application is subject to an IP based concurrent request throttle.
    If a single IP is making more than 30 requests a second, new requests will be dropped.
    The exact ban period is subject to change, but will be on the order of 30 seconds to a few minutes typically.
    Note that exactly what response an application gets (in terms of HTTP code, text, and so on)
    is undefined when subject to this ban; we consider > 30 request/sec per IP to be very abusive and thus cut the requests off very harshly.
    '''
    return requests.get(url, headers=headers)


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
        url = f'https://api.stackoverflowteams.com/2.3/questions?&team={so_config.team_name}'
        response = rate_limited_get(url, headers={'X-API-Access-Token': so_config.api_key})
        response.raise_for_status()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        so_config = StackOverflowConfig(**self._raw_config)
        self._api_key = so_config.api_key
        self._team_name = so_config.team_name

    def _fetch_posts(self, *, api_key: str, team_name: str, page: int, doc_type: str) -> None:
        team_fragment = f'&team={team_name}'
        # this is a filter for "body markdown" inclusion, all filters are unique and static
        # i am not entirely sure if this is per account, or usable by everyone
        filter_fragment = '&filter=!nOedRLbqzB'
        page_fragment = f'&page={page}'
        # it looked like the timestamp was 10 digits, lets only look at stuff that is newer than the last index time
        from_date_fragment = f'&fromdate={self._last_index_time.timestamp():.10n}'
        url = f'https://api.stackoverflowteams.com/2.3/{doc_type}?{team_fragment}{filter_fragment}{page_fragment}{from_date_fragment}'
        response = rate_limited_get(url, headers={'X-API-Access-Token': api_key})
        response.raise_for_status()
        response = response.json()
        has_more = response['has_more']
        items = response['items']
        logger.info(f'Fetched {len(items)} {doc_type} from Stack Overflow')
        for item_dict in items:
            owner_fields = {}
            if 'owner' in item_dict:
                owner_fields = {f"owner_{k}": v for k, v in item_dict.pop('owner').items()}
            if 'title' not in item_dict:
                item_dict['title'] = item_dict['link']
            post = StackOverflowPost(**item_dict, **owner_fields)
            last_modified = datetime.fromtimestamp(post.last_edit_date or post.last_activity_date)
            if last_modified < self._last_index_time:
                return
            logger.info(f'Feeding {doc_type} {post.title}')
            post_document = BasicDocument(title=post.title, content=post.body_markdown, author=post.owner_display_name,
                                          timestamp=datetime.fromtimestamp(post.creation_date), id=post.post_id,
                                          data_source_id=self._data_source_id, location=post.link,
                                          url=post.link, author_image_url=post.owner_profile_image,
                                          type=DocumentType.MESSAGE)
            IndexQueue.get_instance().put_single(doc=post_document)
        if has_more:
            # paginate onto the queue
            self.add_task_to_queue(self._fetch_posts, api_key=self._api_key, team_name=self._team_name, page=page + 1, doc_type=doc_type)

    def _feed_new_documents(self) -> None:
        self.add_task_to_queue(self._fetch_posts, api_key=self._api_key, team_name=self._team_name, page=1, doc_type='articles')
        self.add_task_to_queue(self._fetch_posts, api_key=self._api_key, team_name=self._team_name, page=1, doc_type='posts')


# def test():
#     import os
#     config = {"api_key": os.environ['SO_API_KEY'], "team_name": os.environ['SO_TEAM_NAME']}
#     so = StackOverflowDataSource(config=config, data_source_id=1)
#     so._feed_new_documents()
#
#
# if __name__ == '__main__':
#     test()