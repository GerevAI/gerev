import requests
import concurrent.futures

from typing import Dict

from indexing_queue import IndexingQueue
from data_source_api.basic_document import BasicDocument, DocumentType
from data_source_api.base_data_source import BaseDataSource
from data_source_api.exception import InvalidDataSourceConfig
from pydantic import BaseModel

GITLAB_BASE_URL = "https://gitlab.com/api/v4"
PROJECTS_URL = f"{GITLAB_BASE_URL}/projects?membership=true"


class GitlabConfig(BaseModel):
    api_token: str


class GitlabDataSource(BaseDataSource):
    @staticmethod
    def validate_config(config: Dict) -> None:
        try:
            parsed_config = GitlabConfig(**config)
            session = requests.Session()
            session.headers.update({"PRIVATE-TOKEN": parsed_config.api_token})
            projects_response = session.get(PROJECTS_URL)
            if projects_response.status_code != 200:
                raise ValueError("Invalid api key")
        except (KeyError, ValueError) as e:
            raise InvalidDataSourceConfig from e

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Create a access token with sufficient permissions in https://gitlab.com/-/profile/personal_access_tokens
        self.gitlab_config = GitlabConfig(**self._config)
        self.session = requests.Session()
        self.session.headers.update({"PRIVATE-TOKEN": self.gitlab_config.api_token})

    def _feed_new_documents(self) -> None:
        projects_response = self.session.get(PROJECTS_URL)
        projects = projects_response.json()

        self._parse_projects_in_parallel(projects)

    def _parse_projects_worker(self, projects):

        documents = []

        for project in projects:
            project_id = project["id"]
            issues_url = f"{GITLAB_BASE_URL}/projects/{project_id}/issues"
            issues_response = self.session.get(issues_url)
            issues_json = issues_response.json()

            for issue in issues_json:
                documents.append(BasicDocument(
                    id=issue["id"],
                    data_source_id=self._data_source_id,
                    type=DocumentType.DOCUMENT,
                    title=issue['title'],
                    content=issue["description"],
                    author=issue['author']['name'],
                    author_image_url=issue['author']['avatar_url'],
                    location=project["web_url"],
                    url=issue['web_url'],
                    timestamp=issue["updated_at"]
                ))

            pull_requests_url = f"{GITLAB_BASE_URL}/projects/{project_id}/merge_requests"
            pull_requests_response = self.session.get(pull_requests_url)
            pull_requests_json = pull_requests_response.json()

            for pull_request in pull_requests_json:
                documents.append(BasicDocument(
                    id=pull_request["id"],
                    data_source_id=self._data_source_id,
                    type=DocumentType.DOCUMENT,
                    title=pull_request['title'],
                    content=pull_request["description"],
                    author=pull_request['author']['name'],
                    author_image_url=pull_request['author']['avatar_url'],
                    location=project["web_url"],
                    url=pull_request['web_url'],
                    timestamp=pull_request["updated_at"]
                ))

        IndexingQueue.get().feed(documents)

    def _parse_projects_in_parallel(self, projects):
        workers = 10

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []
            for i in range(workers):
                futures.append(executor.submit(self._parse_project, projects[i::workers]))
            concurrent.futures.wait(futures)
