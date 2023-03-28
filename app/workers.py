import logging
import threading
import time

from data_source.api.context import DataSourceContext
from queues.task_queue import TaskQueue

logger = logging.getLogger()


class Workers:
    _threads = []
    _stop_event = threading.Event()
    WORKER_AMOUNT = 20

    @classmethod
    def start(cls):
        for i in range(cls.WORKER_AMOUNT):
            cls._threads.append(threading.Thread(target=cls.run))
        for thread in cls._threads:
            thread.start()

    @classmethod
    def stop(cls):
        cls._stop_event.set()
        logging.info('Stop event set, waiting for workers to stop...')

        for thread in cls._threads:
            thread.join()
        logging.info('Workers stopped')

        cls._thread = None

    @staticmethod
    def run():
        task_queue = TaskQueue.get_instance()
        logger.info(f'Worker started...')

        while not Workers._stop_event.is_set():
            task_item = task_queue.get_task()
            if not task_item:
                continue

            try:
                data_source = DataSourceContext.get_data_source(task_item.task.data_source_id)
                data_source.run_task(task_item.task.function_name, **task_item.task.kwargs)
                task_queue.ack(id=task_item.queue_item_id)
            except Exception as e:
                logger.exception(f'Failed to ack task {task_item.task.function_name} '
                                 f'for data source {task_item.task.data_source_id}')
                task_queue.nack(id=task_item.queue_item_id)
