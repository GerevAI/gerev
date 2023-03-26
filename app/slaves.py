import logging
import threading

from data_source.context import DataSourceContext
from queues.task_queue import TaskQueue

logger = logging.getLogger()


class Slaves:
    _threads = []
    _stop_event = threading.Event()

    @classmethod
    def start(cls):
        for i in range(0, 20):
            cls._threads.append(threading.Thread(target=cls.run))
        for thread in cls._threads:
            thread.start()

    @classmethod
    def stop(cls):
        cls._stop_event.set()
        logging.info('Stop event set, waiting for slaves to stop...')

        for thread in cls._threads:
            thread.join()
        logging.info('Slaves stopped')

        cls._thread = None

    @staticmethod
    def run():
        task_queue = TaskQueue.get_instance()
        logger.info(f'Slave started...')

        while not Slaves._stop_event.is_set():
            task_item = task_queue.get_task()
            if not task_item:
                continue

            try:
                data_source = DataSourceContext.get_data_source(task_item.task.data_source_id)
                # load kwargs dict to real kwargs
                data_source.run_task(task_item.task.function_name, **task_item.task.kwargs)
                task_queue.ack(id=task_item.queue_item_id)
            except Exception as e:
                logger.exception(f'Failed to ack task {task_item.task.function_name} '
                                 f'for data source {task_item.task.data_source_id}')
                task_queue.nack(id=task_item.queue_item_id)
                import time
                time.sleep(1)
