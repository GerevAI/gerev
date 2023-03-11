from abc import abstractmethod


class DataSource:
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def feed_new_documents(self) -> None:
        raise NotImplementedError
