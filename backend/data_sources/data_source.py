from abc import abstractmethod
from typing import List

from integrations_api import BasicDocument


class DataSource:
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def get_documents(self) -> List[BasicDocument]:
        raise NotImplementedError
