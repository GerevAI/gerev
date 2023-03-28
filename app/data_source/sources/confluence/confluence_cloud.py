from typing import List, Dict
import os

from atlassian import Confluence
from pydantic import BaseModel

from data_source.api.base_data_source import ConfigField, HTMLInputType
from data_source.api.exception import InvalidDataSourceConfig
from data_source.sources.confluence.confluence import ConfluenceDataSource


class ConfluenceCloudConfig(BaseModel):
    url: str
    token: str
    username: str


class ConfluenceCloudDataSource(ConfluenceDataSource):

    @staticmethod
    def get_config_fields() -> List[ConfigField]:
        return [
            ConfigField(label="Confluence URL", name="url", placeholder="https://example.confluence.com"),
            ConfigField(label="Personal API Token", name="token", input_type=HTMLInputType.PASSWORD),
            ConfigField(label="Username", name="username", placeholder="example.user@email.com")
        ]

    @staticmethod
    def validate_config(config: Dict) -> None:
        try:
            parsed_config = ConfluenceCloudConfig(**config)
            confluence = Confluence(url=parsed_config.url, username=parsed_config.username,
                                    password=parsed_config.token, cloud=True)
            ConfluenceCloudDataSource.list_spaces(confluence=confluence)
        except Exception as e:
            raise InvalidDataSourceConfig from e

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        confluence_config = ConfluenceCloudConfig(**self._config)
        should_verify_ssl = os.environ.get('CONFLUENCE_CLOUD_VERIFY_SSL') is not None
        self._confluence = Confluence(url=confluence_config.url, username=confluence_config.username,
                                      password=confluence_config.token, verify_ssl=should_verify_ssl, cloud=True)