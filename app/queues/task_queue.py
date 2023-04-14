import threading
from dataclasses import dataclass
from typing import Optional

from persistqueue import SQLiteAckQueue, Empty

from paths import SQLITE_TASKS_PATH


@dataclass
class Task:
    data_source_id: int
    function_name: str
    kwargs: dict
    attempts: int = 3


@dataclass
class TaskQueueItem:
    queue_item_id: int
    task: Task


class TaskQueue(SQLiteAckQueue):
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        if TaskQueue._instance is not None:
            raise RuntimeError("TaskQueue is a singleton, use .get() to get the instance")

        self.condition = threading.Condition()
        super().__init__(path=SQLITE_TASKS_PATH, multithreading=True, name="task")

    def add_task(self, task: Task):
        self.put(task)

    def get_task(self, timeout=1) -> Optional[TaskQueueItem]:
        try:
            raw_item = super().get(raw=True, block=True, timeout=timeout)
            return TaskQueueItem(queue_item_id=raw_item['pqid'], task=raw_item['data'])

        except Empty:
            return None
