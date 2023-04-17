import logging
import threading
from typing import List

from queues.index_queue import IndexQueue
from indexing.index_documents import Indexer


logger = logging.getLogger()


class BackgroundIndexer:
    _thread = None
    _stop_event = threading.Event()
    _currently_indexing_count = 0
    _total_indexed_count = 0

    @classmethod
    def get_currently_indexing(cls) -> int:
        return cls._currently_indexing_count

    @classmethod
    def get_indexed_count(cls) -> int:
        return cls._total_indexed_count

    @classmethod
    def reset_indexed_count(cls):
        cls._total_indexed_count = 0

    @classmethod
    def start(cls):
        cls._thread = threading.Thread(target=cls.run)
        cls._thread.start()

    @classmethod
    def stop(cls):
        cls._stop_event.set()
        logging.info('Stop event set, waiting for background indexer to stop...')

        cls._thread.join()
        logging.info('Background indexer stopped')

        cls._thread = None

    @staticmethod
    def run():
        docs_queue_instance = IndexQueue.get_instance()
        logger.info(f'Background indexer started...')

        while not BackgroundIndexer._stop_event.is_set():
            try:
                queue_items = docs_queue_instance.consume_all()
                if not queue_items:
                    continue

                BackgroundIndexer._currently_indexing_count = len(queue_items)
                logger.info(f'Got chunk of {len(queue_items)} documents')

                docs = [doc.doc for doc in queue_items]
                Indexer.index_documents(docs)
                BackgroundIndexer._ack_chunk(docs_queue_instance, [doc.queue_item_id for doc in queue_items])
            except Exception as e:
                logger.exception(e)
                logger.error('Error while indexing documents...')

    @staticmethod
    def _ack_chunk(queue: IndexQueue, ids: List[int]):
        logger.info(f'Finished indexing chunk of {len(ids)} documents')
        for item_id in ids:
            queue.ack(id=item_id)

        logger.info(f'Acked {len(ids)} documents.')
        BackgroundIndexer._total_indexed_count += len(ids)
        BackgroundIndexer._currently_indexing_count = 0
