from typing import List, Dict

from atlassian import Jira

from data_source.api.base_data_source import ConfigField, HTMLInputType, Location, BaseDataSourceConfig
from data_source.api.exception import InvalidDataSourceConfig
from data_source.sources.jira.jira import JiraDataSource


class JiraCloudConfig(BaseDataSourceConfig):
    url: str
    token: str
    username: str


class JiraCloudDataSource(JiraDataSource):

    @staticmethod
    def get_config_fields() -> List[ConfigField]:
        return [
            ConfigField(label="Jira Cloud URL", name="url", placeholder="https://example.jira.com"),
            ConfigField(label="Personal API Token", name="token", input_type=HTMLInputType.PASSWORD),
            ConfigField(label="Username", name="username", placeholder="example.user@email.com")
        ]

    @staticmethod
    async def validate_config(config: Dict) -> None:
        try:
            client = JiraCloudDataSource.client_from_config(config)
            JiraCloudDataSource.list_projects(jira=client)
        except Exception as e:
            raise InvalidDataSourceConfig from e

    @classmethod
    def get_display_name(cls) -> str:
        return "Jira Cloud"

    @staticmethod
    def client_from_config(config: Dict) -> Jira:
        parsed_config = JiraCloudConfig(**config)
        return Jira(url=parsed_config.url, username=parsed_config.username,
                    password=parsed_config.token, cloud=True)

    @staticmethod
    def list_locations(config: Dict) -> List[Location]:
        jira = JiraCloudDataSource.client_from_config(config)
        return JiraDataSource.list_projects(jira=jira)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._jira = JiraCloudDataSource.client_from_config(self._raw_config)
