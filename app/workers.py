import logging
import threading

from data_source.api.context import DataSourceContext
from queues.task_queue import TaskQueue, TaskQueueItem, Task

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
            task_item: TaskQueueItem = task_queue.get_task()
            if not task_item:
                continue

            task_data: Task = task_item.task
            try:
                data_source = DataSourceContext.get_data_source_instance(task_data.data_source_id)
                data_source.run_task(task_data.function_name, **task_data.kwargs)
                task_queue.ack(id=task_item.queue_item_id)
            except Exception:
                logger.exception(f'Failed to ack task {task_data.function_name} '
                                 f'for data source {task_data.data_source_id}, decrementing remaining attempts')
                try:
                    task_data.attempts -= 1

                    if task_data.attempts == 0:
                        logger.error(f'max attempts reached, dropping')
                        task_queue.ack_failed(id=task_item.queue_item_id)
                    else:
                        task_queue.update(id=task_item.queue_item_id, item=task_data)
                        task_queue.nack(id=task_item.queue_item_id)
                except Exception:
                    logger.exception('Error while handling task that failed...')
                    task_queue.ack_failed(id=task_item.queue_item_id)
