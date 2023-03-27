import logging
from abc import abstractmethod, ABC
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable
import re

from pydantic import BaseModel

from db_engine import Session
from queues.task_queue import TaskQueue, Task
from schemas import DataSource


class HTMLInputType(Enum):
    TEXT = "text"
    TEXTAREA = "textarea"
    PASSWORD = "password"


class ConfigField(BaseModel):
    name: str
    input_type: HTMLInputType = HTMLInputType.TEXT
    label: Optional[str] = None
    placeholder: Optional[str] = None

    def __init__(self, **data):
        name = data.get("name")
        label = data.get("label") or name.title()
        data["label"] = label
        data["placeholder"] = data.get("placeholder") or label
        super().__init__(**data)

    class Config:
        use_enum_values = True


class BaseDataSource(ABC):

    @staticmethod
    @abstractmethod
    def get_config_fields() -> List[ConfigField]:
        """
        Returns a list of fields that are required to configure the data source for UI.
        for example:
        [
            ConfigField(label="Url", name="url", type="text", placeholder="https://example.com"),
            ConfigField(label="Token", name="token", type="password", placeholder="paste-your-token-here")
        ]
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def validate_config(config: Dict) -> None:
        """
        Validates the config and raises an exception if it's invalid.
        """
        raise NotImplementedError

    @classmethod
    def get_display_name(cls) -> str:
        """
        Returns the display name of the data source, change GoogleDriveDataSource to Google Drive.
        """
        pascal_case_source = cls.__name__.replace("DataSource", "")
        words = re.findall('[A-Z][^A-Z]*', pascal_case_source)
        return " ".join(words)

    @abstractmethod
    def _feed_new_documents(self) -> None:
        """
        Feeds the indexing queue with new documents.
        """
        raise NotImplementedError

    def __init__(self, config: Dict, data_source_id: int, last_index_time: datetime = None) -> None:
        self._config = config
        self._data_source_id = data_source_id

        if last_index_time is None:
            last_index_time = datetime(2012, 1, 1)
        self._last_index_time = last_index_time
        self._last_task_time = None

    def _save_index_time_in_db(self) -> None:
        """
        Sets the index time in the database, to be now
        """
        with Session() as session:
            data_source: DataSource = session.query(DataSource).filter_by(id=self._data_source_id).first()
            data_source.last_indexed_at = datetime.now()
            session.commit()

    def add_task_to_queue(self, function: Callable, **kwargs):
        task = Task(data_source_id=self._data_source_id,
                    function_name=function.__name__,
                    kwargs=kwargs)
        TaskQueue.get_instance().add_task(task)

    def run_task(self, function_name: str, **kwargs) -> None:
        self._last_task_time = datetime.now()
        function = getattr(self, function_name)
        function(**kwargs)

    def index(self, force: bool = False) -> None:
        if self._last_task_time is not None and not force:
            # Don't index if the last task was less than an hour ago
            time_since_last_task = datetime.now() - self._last_task_time
            if time_since_last_task.total_seconds() < 60 * 60:
                logging.info("Skipping indexing data source because it was indexed recently")

        try:
            self._save_index_time_in_db()
            self._feed_new_documents()
        except Exception as e:
            logging.exception("Error while indexing data source")
