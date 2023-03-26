import threading
from dataclasses import dataclass
from typing import List

from persistqueue import SQLiteAckQueue

from data_source_api.basic_document import BasicDocument
from paths import SQLITE_TASKS_PATH


@dataclass
class IndexQueueItem:
    queue_item_id: int
    doc: BasicDocument


class IndexQueue(SQLiteAckQueue):
    __instance = None
    __lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls.__lock:
            if cls.__instance is None:
                cls.__instance = cls()
        return cls.__instance

    def __init__(self):
        if IndexQueue.__instance is not None:
            raise RuntimeError("Queue is a singleton, use .get() to get the instance")

        self.condition = threading.Condition()
        super().__init__(path=SQLITE_TASKS_PATH, multithreading=True, name="index")

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
                raw_items = super().get(raw=True)
                queue_items.append(IndexQueueItem(queue_item_id=raw_items['pqid'], doc=raw_items['data']))
                count += 1

            return queue_items
