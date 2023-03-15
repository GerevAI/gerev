from datetime import datetime
import logging
from abc import abstractmethod, ABC
from typing import Dict

from db_engine import Session
from schemas import DataSource


class BaseDataSource(ABC):

    @staticmethod
    @abstractmethod
    def validate_config(config: Dict) -> None:
        raise NotImplementedError

    @abstractmethod
    def _feed_new_documents(self) -> None:
        raise NotImplementedError

    def __init__(self, config: Dict, data_source_id: int, last_index_time: datetime = datetime(1970, 1, 1)) -> None:
        self._config = config
        self._data_source_id = data_source_id

        if last_index_time is None:
            last_index_time = datetime(1970, 1, 1)
        self._last_index_time = last_index_time

    def _set_last_index_time(self) -> None:
        with Session() as session:
            data_source: DataSource = session.query(DataSource).filter_by(id=self._data_source_id).first()
            data_source.last_indexed_at = datetime.now()
            session.commit()

    def index(self) -> None:
        try:
            self._set_last_index_time()
            self._feed_new_documents()
        except Exception as e:
            logging.error(f"Error while indexing data source {self._data_source_id}: {e}")

