import os
from typing import List, Dict

from atlassian import Confluence

from data_source.api.base_data_source import ConfigField, HTMLInputType, Location, BaseDataSourceConfig
from data_source.api.exception import InvalidDataSourceConfig
from data_source.sources.confluence.confluence import ConfluenceDataSource


class ConfluenceCloudConfig(BaseDataSourceConfig):
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
    async def validate_config(config: Dict) -> None:
        try:
            client = ConfluenceCloudDataSource.confluence_client_from_config(config)
            ConfluenceCloudDataSource.list_spaces(confluence=client)
        except Exception as e:
            raise InvalidDataSourceConfig from e

    @staticmethod
    def confluence_client_from_config(config: Dict) -> Confluence:
        parsed_config = ConfluenceCloudConfig(**config)
        should_verify_ssl = os.environ.get('CONFLUENCE_CLOUD_VERIFY_SSL') is not None
        return Confluence(url=parsed_config.url, username=parsed_config.username,
                          password=parsed_config.token, verify_ssl=should_verify_ssl, cloud=True)

    @staticmethod
    def list_locations(config: Dict) -> List[Location]:
        confluence = ConfluenceCloudDataSource.confluence_client_from_config(config)
        return ConfluenceDataSource.list_all_spaces(confluence=confluence)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._confluence = ConfluenceCloudDataSource.confluence_client_from_config(self._raw_config)
