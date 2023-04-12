import logging

import requests
from typing import Dict, List, Optional
import dateutil.parser

from data_source.api.base_data_source import BaseDataSource, BaseDataSourceConfig, ConfigField, HTMLInputType
from data_source.api.basic_document import BasicDocument, DocumentType, DocumentStatus
from data_source.api.exception import InvalidDataSourceConfig
from queues.index_queue import IndexQueue


logger = logging.getLogger(__name__)


class GitlabConfig(BaseDataSourceConfig):
    url: str
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

    @staticmethod
    def get_config_fields() -> List[ConfigField]:
        return [
            ConfigField(label="Gitlab URL", name="url", input_type=HTMLInputType.TEXT,
                        placeholder="https://gitlab.com"),
            ConfigField(label="API Access Token", name="access_token", input_type=HTMLInputType.PASSWORD),
        ]

    @staticmethod
    def validate_config(config: Dict) -> None:
        try:
            parsed_config = GitlabConfig(**config)
            session = requests.Session()
            session.headers.update({"PRIVATE-TOKEN": parsed_config.access_token})
            projects_response = session.get(f"{parsed_config.url}/api/v4/projects?membership=true")
            projects_response.raise_for_status()
        except (KeyError, ValueError) as e:
            raise InvalidDataSourceConfig from e

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gitlab_config = GitlabConfig(**self._raw_config)
        self._session = requests.Session()
        self._session.headers.update({"PRIVATE-TOKEN": self.gitlab_config.access_token})

    def _get_all_paginated(self, url: str) -> List[Dict]:
        items = []
        page = 1
        per_page = 100

        while True:
            try:
                response = self._session.get(url + f"&per_page={per_page}&page={page}")
                response.raise_for_status()
                new_items: List[Dict] = response.json()
                items.extend(new_items)

                if len(new_items) < per_page:
                    break

                page += 1
            except:
                logging.exception("Error while fetching items paginated for url: " + url)

        return items

    def _list_all_projects(self) -> List[Dict]:
        return self._get_all_paginated(f"{self.gitlab_config.url}/api/v4/projects?membership=true")

    def _feed_new_documents(self) -> None:
        for project in self._list_all_projects():
            logger.info(f"Feeding project {project['name']}")
            self.add_task_to_queue(self._feed_project_issues, project=project)

    def _feed_project_issues(self, project: Dict):
        project_id = project["id"]
        issues_url = f"{self.gitlab_config.url}/api/v4/projects/{project_id}/issues?scope=all"
        all_issues = self._get_all_paginated(issues_url)

        for issue in all_issues:
            self.add_task_to_queue(self.feed_issue, issue=issue)

    def feed_issue(self, issue: Dict):
        updated_at = dateutil.parser.parse(issue["updated_at"])
        if self._is_prior_to_last_index_time(doc_time=updated_at):
            logger.info(f"Issue {issue['id']} is too old, skipping")
            return

        comments_url = \
            f"{self.gitlab_config.url}/api/v4/projects/{issue['project_id']}/issues/{issue['iid']}/notes?sort=asc"
        raw_comments = self._get_all_paginated(comments_url)
        comments = []
        issue_url = issue['web_url']

        for raw_comment in raw_comments:
            if raw_comment["system"]:
                continue

            comments.append(BasicDocument(
                id=raw_comment["id"],
                data_source_id=self._data_source_id,
                type=DocumentType.COMMENT,
                title=raw_comment["author"]["name"],
                content=raw_comment["body"],
                author=raw_comment["author"]["name"],
                author_image_url=raw_comment["author"]["avatar_url"],
                location=issue['references']['full'].replace("/", " / "),
                url=issue_url,
                timestamp=dateutil.parser.parse(raw_comment["updated_at"])
            ))

        status = gitlab_status_to_doc_status(issue["state"])
        is_active = status == DocumentStatus.OPEN
        doc = BasicDocument(
            id=issue["id"],
            data_source_id=self._data_source_id,
            type=DocumentType.ISSUE,
            title=issue['title'],
            content=issue.get("description") or "",
            author=issue['author']['name'],
            author_image_url=issue['author']['avatar_url'],
            location=issue['references']['full'].replace("/", " / "),
            url=issue['web_url'],
            timestamp=updated_at,
            status=issue["state"],
            is_active=is_active,
            children=comments
        )
        IndexQueue.get_instance().put_single(doc=doc)
