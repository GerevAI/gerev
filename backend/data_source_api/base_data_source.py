from abc import abstractmethod
from typing import Dict


class BaseDataSource:
    def __init__(self, data_source_id: int, config: Dict):
        self._data_source_id = data_source_id
        self._config = config

    @staticmethod
    @abstractmethod
    def validate_config(config: Dict) -> None:
        raise NotImplementedError

    @abstractmethod
    def feed_new_documents(self) -> None:
        raise NotImplementedError
