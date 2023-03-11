import logging

from docs_queue import IndexingQueue
from indexing.index_documents import Indexer


class BackgroundIndexer:

    @staticmethod
    def run():
        logger = logging.getLogger()
        docs_queue_instance = IndexingQueue.get()

        while True:
            logger.info(f'Started another iteration of BackgroundIndexer, waiting for documents...')
            docs_chunk = docs_queue_instance.consume_all()
            logger.info(f'Got chunk of {len(docs_chunk)} documents')
            Indexer.index_documents(docs_chunk)
            logger.info(f'Finished indexing chunk of {len(docs_chunk)} documents')
