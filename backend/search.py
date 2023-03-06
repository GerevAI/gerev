from typing import List
from sentence_transformers import SentenceTransformer, CrossEncoder

import integrations_api

from models import Document, Paragraph
from db_engine import Session
from index import Index

bi_encoder = SentenceTransformer('multi-qa-MiniLM-L6-cos-v1')

cross_encoder_small = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-2-v2')
cross_encoder_large = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2')


def index_documents(documents: List[integrations_api.BasicDocument]) -> List[Paragraph]:
    with Session() as session:
        db_documents = []
        for document in documents:
            # Split the content into paragraphs that fit inside the database
            paragraphs = [document.content[i:i+2048] for i in range(0, len(document.content), 2048)]
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
    top_k_ids = list(index.search(query_embedding, 100))[0]
    top_k_ids = [int(id) for id in top_k_ids if id != -1]
    print(top_k_ids)
    # Get the paragraphs from the database
    session = Session()
    paragraphs = session.query(Paragraph).filter(Paragraph.id.in_(top_k_ids)).all()

    if len(paragraphs) == 0:
        return []

    # calculate small cross-encoder scores to leave just 10 candidates
    small_scores = cross_encoder_small.predict([(query, p.content) for p in paragraphs])
    candidates = [{
        'paragraph': p,
        'score': s
    } for p, s in zip(paragraphs, small_scores)]
    candidates.sort(key=lambda c: c['score'], reverse=True)

    candidates = candidates[:10]

    # calculate large cross-encoder scores to leave just top_k candidates
    large_scores = cross_encoder_large.predict([(query, c['paragraph'].content) for c in candidates])
    candidates = [{
        'paragraph': c['paragraph'],
        'score': s
    } for c, s in zip(candidates, large_scores)]
    candidates.sort(key=lambda c: c['score'], reverse=True)

    return [c['paragraph'] for c in candidates[:top_k]]
