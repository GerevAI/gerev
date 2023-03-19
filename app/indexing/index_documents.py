import logging
import re
from typing import List

from data_source_api.basic_document import BasicDocument
from paths import IS_IN_DOCKER
from schemas import Document, Paragraph
from models import bi_encoder
from indexing.faiss_index import FaissIndex
from indexing.bm25_index import Bm25Index
from db_engine import Session


class Indexer:

    @staticmethod
    def index_documents(documents: List[BasicDocument]):
        logging.getLogger().info(f"Indexing {len(documents)} documents")

        with Session() as session:
            db_documents = []
            for document in documents:
                # Split the content into paragraphs that fit inside the database
                paragraphs = Indexer._split_into_paragraphs(document.content)
                # Create a new document in the database
                db_document = Document(
                    data_source_id=document.data_source_id,
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
            paragraphs = [paragraph for document in db_documents for paragraph in document.paragraphs]
            paragraph_ids = [paragraph.id for paragraph in paragraphs]
            paragraph_contents = [Indexer._add_metadata_for_indexing(paragraph) for paragraph in paragraphs]

        Bm25Index.get().update()

        # Encode the paragraphs
        show_progress_bar = not IS_IN_DOCKER
        embeddings = bi_encoder.encode(paragraph_contents, convert_to_tensor=True, show_progress_bar=show_progress_bar)

        # Add the embeddings to the index
        FaissIndex.get().update(paragraph_ids, embeddings)

        logging.getLogger().info(f"Indexed {len(paragraphs)} paragraphs")

    @staticmethod
    def _split_into_paragraphs(text, minimum_length=256):
        """
        split into paragraphs and batch small paragraphs together into the same paragraph
        """
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
