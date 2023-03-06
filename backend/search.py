import torch

from typing import List
from sentence_transformers import SentenceTransformer, CrossEncoder

import integrations_api

from schemas import Document, Paragraph
from db_engine import Session
from index import Index
from models import bi_encoder, cross_encoder_small, cross_encoder_large

BI_ENCODER_CANDIDATES = 100 if torch.cuda.is_available() else 50
SMALL_CROSS_ENCODER_CANDIDATES = 20 if torch.cuda.is_available() else 10


def _split_into_paragraphs(text, minimum_length=256):
    """
    split into paragraphs and batch small paragraphs together into the same paragraph
    """
    paragraphs = []
    current_paragraph = ''
    for paragraph in text.split('\n\n'):
        current_paragraph += paragraph

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
    index = Index.get()
    index.update(paragraph_ids, embeddings)


def _cross_encode(
        cross_encoder: CrossEncoder,
        encoded_query: torch.LongTensor,
        paragraphs: List[Paragraph],
        top_k: int) -> List[Paragraph]:
    scores = cross_encoder.predict([(encoded_query, paragraph.content) for paragraph in paragraphs])
    candidates = [{
        'paragraph': paragraph,
        'score': score
    } for paragraph, score in zip(paragraphs, scores)]
    candidates.sort(key=lambda c: c['score'], reverse=True)
    return [candidate['paragraph'] for candidate in candidates[:top_k]]


def search_documents(query: str, top_k: int) -> List[Paragraph]:
    # Encode the query
    query_embedding = bi_encoder.encode(query, convert_to_tensor=True)

    # Search the index for 100 candidates
    index = Index.get()
    results = index.search(query_embedding, BI_ENCODER_CANDIDATES)
    results = results[0]
    results = [id for id in results if id != -1]  # filter out empty results

    # Get the paragraphs from the database
    with Session() as session:
        paragraphs = session.query(Paragraph).filter(Paragraph.id.in_(results)).all()

    if len(paragraphs) == 0:
        return []

    # calculate small cross-encoder scores to leave just a few candidates
    candidates = _cross_encode(cross_encoder_small, query_embedding, paragraphs, SMALL_CROSS_ENCODER_CANDIDATES)
    # calculate large cross-encoder scores to leave just top_k candidates
    candidates = _cross_encode(cross_encoder_large, query_embedding, candidates, top_k)

    return candidates
