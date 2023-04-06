import logging
import re
from typing import List

from data_source.api.basic_document import BasicDocument
from paths import IS_IN_DOCKER
from schemas import Document, Paragraph
from models import bi_encoder
from indexing.faiss_index import FaissIndex
from indexing.bm25_index import Bm25Index
from db_engine import Session


logger = logging.getLogger(__name__)


class Indexer:

    @staticmethod
    def index_documents(documents: List[BasicDocument]):
        logger.info(f"Indexing {len(documents)} documents")

        ids_in_data_source = [document.id_in_data_source for document in documents]

        with Session() as session:
            documents_to_delete = session.query(Document).filter(Document.id_in_data_source.in_(ids_in_data_source)).all()
            if documents_to_delete:
                logging.info(f'removing documents that were updated and need to be re-indexed.')
                Indexer.remove_documents(documents_to_delete, session)
                for document in documents_to_delete:
                    # Currently bulk deleting doesn't cascade. So we need to delete them one by one.
                    # See https://stackoverflow.com/a/19245058/3541901
                    session.delete(document)
                session.commit()

        with Session() as session:
            db_documents = []
            for document in documents:
                # Split the content into paragraphs that fit inside the database
                paragraphs = Indexer._split_into_paragraphs(document.content)
                # Create a new document in the database
                db_document = Document(
                    data_source_id=document.data_source_id,
                    id_in_data_source=document.id_in_data_source,
                    type=document.type.value,
                    file_type=document.file_type.value if document.file_type is not None else None,
                    title=document.title,
                    author=document.author,
                    author_image_url=document.author_image_url,
                    location=document.location,
                    url=document.url,
                    timestamp=document.timestamp,
                    paragraphs=[
                        Paragraph(content=content)
                        for content in paragraphs
                    ]
                )

                db_documents.append(db_document)

            # Save the documents to the database
            session.add_all(db_documents)
            session.commit()

            # Create a list of all the paragraphs in the documents
            logger.info(f"Indexing {len(db_documents)} documents => {len(paragraphs)} paragraphs")
            paragraphs = [paragraph for document in db_documents for paragraph in document.paragraphs]
            if len(paragraphs) == 0:
                logger.info(f"No paragraphs to index")
                return

            paragraph_ids = [paragraph.id for paragraph in paragraphs]
            paragraph_contents = [Indexer._add_metadata_for_indexing(paragraph) for paragraph in paragraphs]

        logger.info(f"Updating BM25 index...")
        Bm25Index.get().update()

        if len(paragraph_contents) == 0:
            return

        # Encode the paragraphs
        show_progress_bar = not IS_IN_DOCKER
        logger.info(f"Encoding with bi-encoder...")
        embeddings = bi_encoder.encode(paragraph_contents, convert_to_tensor=True, show_progress_bar=show_progress_bar)

        # Add the embeddings to the index
        logger.info(f"Updating Faiss index...")
        FaissIndex.get().update(paragraph_ids, embeddings)

        logger.info(f"Finished indexing {len(documents)} documents => {len(paragraphs)} paragraphs")

    @staticmethod
    def _split_into_paragraphs(text, minimum_length=256):
        """
        split into paragraphs and batch small paragraphs together into the same paragraph
        """
        if text is None:
            return []
        paragraphs = []
        current_paragraph = ''
        for paragraph in re.split(r'\n\s*\n', text):
            if len(current_paragraph) > 0:
                current_paragraph += ' '
            current_paragraph += paragraph.strip()

            if len(current_paragraph) > minimum_length:
                paragraphs.append(current_paragraph)
                current_paragraph = ''

        if len(current_paragraph) > 0:
            paragraphs.append(current_paragraph)

        return paragraphs

    @staticmethod
    def _add_metadata_for_indexing(paragraph: Paragraph) -> str:
        result = paragraph.content
        if paragraph.document.title is not None:
            result += '; ' + paragraph.document.title
        return result

    @staticmethod
    def remove_documents(documents: List[Document], session = None):
        logger.info(f"Removing {len(documents)} documents")

        # Get the paragraphs from the documents
        db_paragraphs = [paragraph for document in documents for paragraph in document.paragraphs]

        # Remove the paragraphs from the index
        paragraph_ids = [paragraph.id for paragraph in db_paragraphs]

        logger.info(f"Removing documents from faiss index...")
        FaissIndex.get().remove(paragraph_ids)

        logger.info(f"Removing documents from BM25 index...")
        Bm25Index.get().update(session=session)

        logger.info(f"Finished removing {len(documents)} documents => {len(db_paragraphs)} paragraphs")