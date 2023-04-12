import logging
import os
import urllib
from typing import List, Dict
import dateutil.parser

import dateutil
from atlassian import Jira
from atlassian.errors import ApiError

from data_source.api.base_data_source import BaseDataSource, ConfigField, HTMLInputType, Location, BaseDataSourceConfig
from data_source.api.basic_document import BasicDocument, DocumentType, DocumentStatus
from data_source.api.exception import InvalidDataSourceConfig
from queues.index_queue import IndexQueue


class JiraConfig(BaseDataSourceConfig):
    url: str
    token: str


logger = logging.getLogger(__name__)


class JiraDataSource(BaseDataSource):

    @classmethod
    def get_display_name(cls) -> str:
        return "Jira Self-Hosted"

    @staticmethod
    def get_config_fields() -> List[ConfigField]:
        return [
            ConfigField(label="Jira URL", name="url", placeholder="https://self-hosted-jira.com"),
            ConfigField(label="Personal Access Token", name="token", input_type=HTMLInputType.PASSWORD)
        ]

    @staticmethod
    def list_projects(jira: Jira) -> List[Location]:
        logger.info('Listing projects')
        projects = jira.get_all_projects()
        return [Location(label=project['name'], value=project['key']) for project in projects]

    @staticmethod
    def list_locations(config: Dict) -> List[Location]:
        jira = JiraDataSource.client_from_config(config)
        return JiraDataSource.list_projects(jira=jira)

    @staticmethod
    def client_from_config(config: Dict) -> Jira:
        parsed_config = JiraConfig(**config)
        should_verify_ssl = os.environ.get('JIRA_VERIFY_SSL') is not None
        return Jira(url=parsed_config.url, token=parsed_config.token, verify_ssl=should_verify_ssl)

    @staticmethod
    def has_prerequisites() -> bool:
        return True

    @staticmethod
    def validate_config(config: Dict) -> None:
        try:
            jira = JiraDataSource.client_from_config(config)
            jira.get_all_priorities()
        except ApiError as e:
            raise InvalidDataSourceConfig from e

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._jira = JiraDataSource.client_from_config(self._raw_config)

    def _feed_new_documents(self) -> None:
        logger.info('Feeding new documents with Jira')
        projects = self._config.locations_to_index or JiraDataSource.list_projects(jira=self._jira)
        for project in projects:
            self.add_task_to_queue(self._feed_project_issues, project=project)

    def _feed_project_issues(self, project: Location):
        logging.info(f'Getting issues from project {project.label} ({project.value})')

        start = 0
        limit = 100
        last_index_time = self._last_index_time.strftime("%Y-%m-%d %H:%M")
        jql_query = f'project = "{project.value}" AND updated >= "{last_index_time}" ORDER BY updated DESC'
        logger.info(f'Querying jira with JQL: {jql_query}')
        while True:
            new_batch = self._jira.jql_get_list_of_tickets(jql_query, start=start, limit=limit, validate_query=True)
            len_new_batch = len(new_batch)
            logger.info(f'Got {len_new_batch} issues from project {project.label} (total {start + len_new_batch})')
            for raw_issue in new_batch:
                self.add_task_to_queue(self._feed_issue, raw_issue=raw_issue, project_name=project.label)

            if len(new_batch) < limit:
                break

            start += limit

    def _feed_issue(self, raw_issue: Dict, project_name: str):
        issue_id = raw_issue['id']
        last_modified = dateutil.parser.parse(raw_issue['fields']['updated'])

        base_url = self._raw_config['url']
        issue_url = urllib.parse.urljoin(base_url, f"/browse/{raw_issue['key']}")
        comments = []
        raw_comments = self._jira.issue_get_comments(issue_id)
        for raw_comment in raw_comments['comments']:
            comments.append(BasicDocument(
                id=raw_comment["id"],
                data_source_id=self._data_source_id,
                type=DocumentType.COMMENT,
                title=raw_comment["author"]["displayName"],
                content=raw_comment["body"],
                author=raw_comment["author"]["displayName"],
                author_image_url=raw_comment["author"]["avatarUrls"]["48x48"],
                location=raw_issue['key'],
                url=issue_url,
                timestamp=dateutil.parser.parse(raw_comment["updated"])
            ))

        author = None
        if assignee := raw_issue['fields'].get('assignee'):
            author = assignee
        elif reporter := raw_issue['fields'].get('reporter'):
            author = reporter
        elif creator := raw_issue['fields'].get('creator'):
            author = creator

        if author:
            author_name = author['displayName']
            author_image_url = author['avatarUrls']['48x48']
        else:
            author_name = 'Unknown'
            author_image_url = ""

        content = raw_issue['fields']['description']
        title = raw_issue['fields']['summary']
        doc = BasicDocument(title=title,
                            content=content,
                            author=author_name,
                            author_image_url=author_image_url,
                            timestamp=last_modified,
                            id=issue_id,
                            data_source_id=self._data_source_id,
                            location=project_name,
                            url=issue_url,
                            status=raw_issue['fields']['status']['name'],
                            type=DocumentType.ISSUE,
                            children=comments)
        IndexQueue.get_instance().put_single(doc=doc)


# if __name__ == '__main__':
#     import os
#     ds = JiraDataSource(config={"url": os.getenv('JIRA_URL'), "token": os.getenv('JIRA_TOKEN')}, data_source_id=5)
#     projects = ds.list_projects(ds._jira)
#     for project in projects:
#         ds._feed_project_issues(project=project)
