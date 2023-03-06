import torch

from typing import List
from sentence_transformers import SentenceTransformer, CrossEncoder

import integrations_api

from schemas import Document, Paragraph
from db_engine import Session
from index import Index
from models import bi_encoder, cross_encoder_small, cross_encoder_large

SMALL_CROSS_ENCODER_CANDIDATES = 100 if torch.cuda.is_available() else 50
LARGE_CROSS_ENCODER_CANDIDATES = 20 if torch.cuda.is_available() else 10


def split_into_paragraphs(text, minimum_length=256):
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
            paragraphs = split_into_paragraphs(document.content)
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


def search_documents(query: str, top_k: int) -> List[Paragraph]:
    # Encode the query
    query_embedding = bi_encoder.encode(query, convert_to_tensor=True)

    # Search the index for 100 candidates
    index = Index.get()
    top_k_ids = list(index.search(query_embedding, SMALL_CROSS_ENCODER_CANDIDATES))[0]
    top_k_ids = [int(id) for id in top_k_ids if id != -1]
    # Get the paragraphs from the database
    session = Session()
    paragraphs = session.query(Paragraph).filter(Paragraph.id.in_(top_k_ids)).all()

    if len(paragraphs) == 0:
        return []

    # calculate small cross-encoder scores to leave just a few candidates
    small_scores = cross_encoder_small.predict([(query, p.content) for p in paragraphs])
    candidates = [{
        'paragraph': p,
        'score': s
    } for p, s in zip(paragraphs, small_scores)]
    candidates.sort(key=lambda c: c['score'], reverse=True)

    candidates = candidates[:LARGE_CROSS_ENCODER_CANDIDATES]

    # calculate large cross-encoder scores to leave just top_k candidates
    large_scores = cross_encoder_large.predict([(query, c['paragraph'].content) for c in candidates])
    candidates = [{
        'paragraph': c['paragraph'],
        'score': s
    } for c, s in zip(candidates, large_scores)]
    candidates.sort(key=lambda c: c['score'], reverse=True)

    return [c['paragraph'] for c in candidates[:top_k]]
