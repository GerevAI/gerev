import logging
from datetime import datetime

import requests
from typing import Dict, List, Optional

from data_source.api.base_data_source import BaseDataSource, BaseDataSourceConfig, ConfigField, HTMLInputType
from data_source.api.basic_document import BasicDocument, DocumentType, DocumentStatus
from data_source.api.exception import InvalidDataSourceConfig
from queues.index_queue import IndexQueue

GITLAB_BASE_URL = "https://gitlab.com/api/v4"

logger = logging.getLogger(__name__)


class GitlabConfig(BaseDataSourceConfig):
    access_token: str


def gitlab_status_to_doc_status(status: str) -> Optional[DocumentStatus]:
    if status == "opened":
        return DocumentStatus.OPEN
    elif status == "closed":
        return DocumentStatus.CLOSED
    else:
        logger.warning(f"[!] Unknown status {status}")
        return None


class GitlabDataSource(BaseDataSource):

    def _feed_project_issues(self, project: Dict):
        project_id = project["id"]
        project_url = project["web_url"]

        issues_url = f"{GITLAB_BASE_URL}/projects/{project_id}/issues"

        issues_response = self._session.get(issues_url)
        issues_response.raise_for_status()
        issues_json = issues_response.json()

        for issue in issues_json:
            last_modified = datetime.strptime(issue["updated_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
            if last_modified < self._last_index_time:
                logger.info(f"Issue {issue['id']} is too old, skipping")
                continue

            doc = BasicDocument(
                id=issue["id"],
                data_source_id=self._data_source_id,
                type=DocumentType.ISSUE,
                title=issue['title'],
                content=issue["description"] if not None else "",
                author=issue['author']['name'],
                author_image_url=issue['author']['avatar_url'],
                location=issue['references']['full'].replace("/", " / "),
                url=issue['web_url'],
                timestamp=last_modified,
                status=gitlab_status_to_doc_status(issue["state"])
            )
            IndexQueue.get_instance().put_single(doc=doc)

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
            projects_response = session.get(f"{GITLAB_BASE_URL}/projects?membership=true")
            projects_response.raise_for_status()
        except (KeyError, ValueError) as e:
            raise InvalidDataSourceConfig from e

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gitlab_config = GitlabConfig(**self._raw_config)
        self._session = requests.Session()
        self._session.headers.update({"PRIVATE-TOKEN": self.gitlab_config.access_token})

    def _list_all_projects(self) -> List[Dict]:
        projects = []
        page = 1
        per_page = 100

        while True:
            try:
                projects_response = self._session.get(f"{GITLAB_BASE_URL}/projects?membership=true"
                                                      f"&per_page={per_page}&page={page}")
                projects_response.raise_for_status()
                new_projects: List[Dict] = projects_response.json()
                projects.extend(new_projects)

                if len(new_projects) < per_page:
                    break

                page += 1
            except:
                logging.exception("Error while fetching projects")

        return projects

    def _feed_new_documents(self) -> None:
        for project in self._list_all_projects():
            logger.info(f"Feeding project {project['name']}")
            self.add_task_to_queue(self._feed_project_issues, project=project)
