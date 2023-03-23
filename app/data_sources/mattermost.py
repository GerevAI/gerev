import logging
from datetime import datetime
from urllib.parse import urlparse
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from functools import lru_cache

from mattermostdriver import Driver

from data_source_api.base_data_source import BaseDataSource, ConfigField, HTMLInputType
from data_source_api.basic_document import BasicDocument, DocumentType
from data_source_api.exception import InvalidDataSourceConfig
from data_source_api.utils import parse_with_workers
from indexing_queue import IndexingQueue


logger = logging.getLogger(__name__)


@dataclass
class MattermostChannel:
    id: str
    name: str
    team_id: str

@dataclass
class MattermostConfig:
    url: str
    token: str
    scheme: Optional[str] = "https"
    port: Optional[int] = 443
    
    def __post_init__(self):
        try:
            parsed_url = urlparse(self.url)
        except Exception as e:
            raise ValueError from e
        
        self.url = parsed_url.hostname
        self.port = parsed_url.port if parsed_url.port is not None else self.port
        self.scheme = parsed_url.scheme if parsed_url.scheme != "" else self.scheme

        

class MattermostDataSource(BaseDataSource):
    FEED_BATCH_SIZE = 500

    @staticmethod
    def get_config_fields() -> List[ConfigField]:
        return [
            ConfigField(label="Mattermost Server", name="url", placeholder="https://mattermost.server.com", input_type=HTMLInputType.TEXT),
            ConfigField(label="Token", name="token", placeholder="paste-your-token-here", input_type=HTMLInputType.PASSWORD),
        ]


    @staticmethod
    def validate_config(config: Dict) -> None:
        try:
            parsed_config = MattermostConfig(**config)
            maattermost = Driver(options = asdict(parsed_config))
            maattermost.login()
        except Exception as e:
            raise InvalidDataSourceConfig from e

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        mattermost_config = MattermostConfig(**self._config)
        self._mattermost = Driver(options = asdict(mattermost_config))
    
    
    def _list_channels(self) -> List[MattermostChannel]:
        channels = self._mattermost.channels.client.get("/channels")
        return [MattermostChannel(id=channel["id"], name=channel["name"], team_id=channel["team_id"])
                for channel in channels]


    def _is_valid_message(self, message: Dict) -> bool:
        return message["type"] == ""
    
    
    def _list_posts_in_channel(self, channel_id: str, page: int) -> Dict:
        endpoint = f"/channels/{channel_id}/posts"
        params = {
            "since": int(self._last_index_time.timestamp()),
            "page": page
        }
        
        posts = self._mattermost.channels.client.get(endpoint, params=params)
        return posts


    def _feed_new_documents(self) -> None:
        self._mattermost.login()
        channels = self._list_channels()
    
        logger.info(f'Found {len(channels)} channels')
        parse_with_workers(self._parse_channel_worker, channels)

    
    def _parse_channel_worker(self, channels: List[MattermostChannel]):        
        for channel in channels:
            self._feed_channel(channel)

    
    def _get_mattermost_url(self):
        options = self._mattermost.options
        return f"{options['scheme']}://{options['url']}:{options['port']}"


    def _get_team_url(self, channel: MattermostChannel):
        url = self._get_mattermost_url()
        team = self._mattermost.teams.get_team(channel.team_id)
        return f"{url}/{team['name']}"
    
    
    @lru_cache(maxsize=512)
    def _get_mattermost_user(self, user_id: str):
        return self._mattermost.users.get_user(user_id)["username"]
    
        
    def _feed_channel(self, channel: MattermostChannel):
        logger.info(f'Feeding channel {channel.name}')
        
        page = 0
        total_fed = 0
        
        parsed_posts = []
        
        team_url = self._get_team_url(channel)
        
        while True:
            posts = self._list_posts_in_channel(channel.id, page)

            last_message: Optional[BasicDocument] = None
            
            posts["order"].reverse()
            for id in posts["order"]:
                post = posts["posts"][id]
                
                if not self._is_valid_message(post):
                    if last_message is not None:
                        parsed_posts.append(last_message)
                        last_message = None
                    continue
                
                author = self._get_mattermost_user(post["user_id"])
                content = post["message"]
                
                if last_message is not None:
                    if last_message.author == author:
                        last_message.content += f"\n{content}"
                        continue
                    else:
                        parsed_posts.append(last_message)
                        if len(parsed_posts) >= MattermostDataSource.FEED_BATCH_SIZE:
                            total_fed += len(parsed_posts)
                            IndexingQueue.get().feed(docs=parsed_posts)
                            parsed_posts = []
                    
                author_image_url = f"{self._get_mattermost_url()}/api/v4/users/{post['user_id']}/image?_=0"
                timestamp = datetime.fromtimestamp(post["update_at"] / 1000)
                last_message = BasicDocument(
                    id=id,
                    data_source_id=self._data_source_id,
                    title=channel.name,
                    content=content,
                    timestamp=timestamp,
                    author=author,
                    author_image_url=author_image_url,
                    location=channel.name,
                    url=f"{team_url}/pl/{id}",
                    type=DocumentType.MESSAGE
                )
                
            if last_message is not None:
                parsed_posts.append(last_message)

            if posts["prev_post_id"] == "":
                break
            page += 1
        

        IndexingQueue.get().feed(docs=parsed_posts)
        total_fed += len(parsed_posts)

        if len(parsed_posts) > 0:
            logger.info(f"Worker fed {total_fed} documents")
            
