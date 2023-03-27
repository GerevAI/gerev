import threading
from dataclasses import dataclass
from typing import List

from persistqueue import SQLiteAckQueue

from data_source.api.basic_document import BasicDocument
from paths import SQLITE_INDEXING_PATH


@dataclass
class IndexQueueItem:
    queue_item_id: int
    doc: BasicDocument


class IndexQueue(SQLiteAckQueue):
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        if IndexQueue._instance is not None:
            raise RuntimeError("Queue is a singleton, use .get() to get the instance")

        self.condition = threading.Condition()
        super().__init__(path=SQLITE_INDEXING_PATH, multithreading=True, name="index")

    def put_single(self, doc: BasicDocument):
        self.put([doc])

    def put(self, docs: List[BasicDocument]):
        with self.condition:
            for doc in docs:
                super().put(doc)

            self.condition.notify_all()

    def consume_all(self, max_docs=5000, timeout=1) -> List[IndexQueueItem]:
        with self.condition:
            self.condition.wait(timeout=timeout)

            queue_items = []
            count = 0
            while not super().empty() and count < max_docs:
                raw_item = super().get(raw=True)
                queue_items.append(IndexQueueItem(queue_item_id=raw_item['pqid'], doc=raw_item['data']))
                count += 1

            return queue_items
