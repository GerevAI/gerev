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


@dataclass
class TaskQueueItem:
    queue_item_id: int
    task: Task


class TaskQueue(SQLiteAckQueue):
    __instance = None
    __lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls.__lock:
            if cls.__instance is None:
                cls.__instance = cls()
        return cls.__instance

    def __init__(self):
        if TaskQueue.__instance is not None:
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
