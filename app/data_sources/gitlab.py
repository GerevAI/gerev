from datetime import datetime

import requests
import concurrent.futures

from typing import Dict, List

from indexing_queue import IndexingQueue
from data_source_api.basic_document import BasicDocument, DocumentType
from data_source_api.base_data_source import BaseDataSource, ConfigField, HTMLInputType
from data_source_api.exception import InvalidDataSourceConfig
from pydantic import BaseModel

GITLAB_BASE_URL = "https://gitlab.com/api/v4"
PROJECTS_URL = f"{GITLAB_BASE_URL}/projects?membership=true"


class GitlabConfig(BaseModel):
    access_token: str


class GitlabDataSource(BaseDataSource):

    def _parse_issues(self, documents: [], project_id: str, project_url: str):
        issues_url = f"{GITLAB_BASE_URL}/projects/{project_id}/issues"

        issues_response = self._session.get(issues_url)
        issues_response.raise_for_status()
        issues_json = issues_response.json()

        for issue in issues_json:
            last_modified = datetime.strptime(issue["updated_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
            if last_modified < self._last_index_time:
                continue

            documents.append(BasicDocument(
                id=issue["id"],
                data_source_id=self._data_source_id,
                type=DocumentType.GIT_ISSUE,
                title=issue['title'],
                content=issue["description"] if not None else "",
                author=issue['author']['name'],
                author_image_url=issue['author']['avatar_url'],
                location=project_url,
                url=issue['web_url'],
                timestamp=last_modified
            ))

    def _parse_pull_requests(self, documents: [], project_id: str, project_url: str):
        pull_requests_url = f"{GITLAB_BASE_URL}/projects/{project_id}/merge_requests"

        pull_requests_response = self._session.get(pull_requests_url)
        pull_requests_response.raise_for_status()
        pull_requests_json = pull_requests_response.json()

        for pull_request in pull_requests_json:
            last_modified = datetime.strptime(pull_request["updated_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
            if last_modified < self._last_index_time:
                continue

            documents.append(BasicDocument(
                id=pull_request["id"],
                data_source_id=self._data_source_id,
                type=DocumentType.GIT_PR,
                title=pull_request['title'],
                content=pull_request["description"] if not None else "",
                author=pull_request['author']['name'],
                author_image_url=pull_request['author']['avatar_url'],
                location=project_url,
                url=pull_request['web_url'],
                timestamp=last_modified
            ))

    @staticmethod
    def get_config_fields() -> List[ConfigField]:
        return [
            ConfigField(label="API Access Token", name="access_token", input_type=HTMLInputType.PASSWORD),
        ]

    @staticmethod
    def validate_config(config: Dict) -> None:
        try:
            parsed_config = GitlabConfig(**config)
            session = requests.Session()
            session.headers.update({"PRIVATE-TOKEN": parsed_config.access_token})
            projects_response = session.get(PROJECTS_URL)
            projects_response.raise_for_status()
        except (KeyError, ValueError) as e:
            raise InvalidDataSourceConfig from e

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Create a access token with sufficient permissions in https://gitlab.com/-/profile/personal_access_tokens
        self.gitlab_config = GitlabConfig(**self._config)
        self._session = requests.Session()
        self._session.headers.update({"PRIVATE-TOKEN": self.gitlab_config.access_token})

    def _feed_new_documents(self) -> None:
        projects_response = self._session.get(PROJECTS_URL)
        projects_response.raise_for_status()
        projects = projects_response.json()

        self._parse_projects_in_parallel(projects)

    def _parse_projects_worker(self, projects):

        documents = []

        for project in projects:
            project_id = project["id"]
            project_url = project["web_url"]
            self._parse_issues(documents, project_id, project_url)
            self._parse_pull_requests(documents, project_id, project_url)

        IndexingQueue.get().feed(documents)

    def _parse_projects_in_parallel(self, projects):
        workers = 10

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []
            for i in range(workers):
                futures.append(executor.submit(self._parse_projects_worker, projects[i::workers]))
            concurrent.futures.wait(futures)
