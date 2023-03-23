import logging
from datetime import datetime
from urllib.parse import urlparse
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

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
    
    
    def _list_posts_in_channel(self, channel_id: str, page: int) -> Dict: #-> List[MattermostPost]:
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
        return f"{url}/{channel.team_id}"
        

    def _feed_channel(self, channel: MattermostChannel):
        logger.info(f'Feeding channel {channel.name}')
        
        page = 0
        total_fed = 0
        
        parsed_posts = []
        
        team_url = self._get_team_url(channel)
        while True:
            posts = self._list_posts_in_channel(channel.id, page)

            for id, post in posts["posts"].items():
                if not self._is_valid_message(post):
                    continue
                
                author = self._mattermost.users.get_user(post["user_id"])["username"]
                author_image_url = f"{self._get_mattermost_url()}/api/v4/users/{post['user_id']}/image?_=0"
                content = post["message"]
                timestamp = datetime.fromtimestamp(post["update_at"] / 1000)
                parsed_posts.append(
                    BasicDocument(
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
                )
                
                if len(parsed_posts) >= self.FEED_BATCH_SIZE:
                    total_fed += len(parsed_posts)
                    IndexingQueue.get().feed(docs=parsed_posts)
                    parsed_posts = []
                
            if posts["prev_post_id"] == "":
                break
            page += 1
        
        IndexingQueue.get().feed(docs=parsed_posts)
        total_fed += len(parsed_posts)
        if len(parsed_posts) > 0:
            logger.info(f"Worker fed {total_fed} documents")
            
