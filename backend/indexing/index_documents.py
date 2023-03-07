import logging
from typing import List

import integrations_api
from schemas import Document, Paragraph
from models import bi_encoder
from indexing.faiss_index import FaissIndex
from db_engine import Session


def _split_into_paragraphs(text, minimum_length=512):
    """
    split into paragraphs and batch small paragraphs together into the same paragraph
    """
    paragraphs = []
    current_paragraph = ''
    for paragraph in text.split('\n\n'):
        current_paragraph += ' ' + paragraph

        if len(current_paragraph) > minimum_length:
            paragraphs.append(current_paragraph)
            current_paragraph = ''
    return paragraphs


def index_documents(documents: List[integrations_api.BasicDocument]) -> List[Paragraph]:
    with Session() as session:
        db_documents = []
        for document in documents:
            # Split the content into paragraphs that fit inside the database
            paragraphs = _split_into_paragraphs(document.content)
            # Create a new document in the database
            db_document = Document(
                integration_name=document.integration_name,
                integration_id=document.id,
                title=document.title,
                author=document.author,
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
        paragraphs = [p for d in db_documents for p in d.paragraphs]
        paragraph_ids = [p.id for p in paragraphs]
        paragraph_contents = [p.content for p in paragraphs]

    # Encode the paragraphs
    embeddings = bi_encoder.encode(paragraph_contents, convert_to_tensor=True)

    # Add the embeddings to the index
    index = FaissIndex.get()
    index.update(paragraph_ids, embeddings)
    logging.getLogger().info(f"Indexed {len(paragraphs)} paragraphs")
