import torch
import nltk

from typing import List
from dataclasses import dataclass
from sentence_transformers import CrossEncoder

from schemas import Paragraph
from db_engine import Session
from indexing.faiss_index import FaissIndex
from models import bi_encoder, cross_encoder_small, cross_encoder_large

BI_ENCODER_CANDIDATES = 100 if torch.cuda.is_available() else 50
SMALL_CROSS_ENCODER_CANDIDATES = 20 if torch.cuda.is_available() else 10

nltk.download('punkt')


@dataclass
class ResultPresentation:
    content: str
    bold: bool


@dataclass
class Candidate:
    content: str
    score: float = 0.0
    representation: List[ResultPresentation] = None

    def to_api(self) -> dict:
        return {
            'score': self.score,
            'content': self.representation
        }


def _cross_encode(
        cross_encoder: CrossEncoder,
        query: str,
        candidates: List[Candidate],
        top_k: int) -> List[Candidate]:
    scores = cross_encoder.predict([(query, candidate.content) for candidate in candidates])
    for candidate, score in zip(candidates, scores):
        candidate.score = score.item()
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:top_k]


def _find_answers_in_candidates(candidates: List[Candidate], query: str) -> List[Candidate]:
    for candidate in candidates:
        sentences = nltk.sent_tokenize(candidate.content)
        scores = cross_encoder_small.predict([(query, sent) for sent in sentences], convert_to_tensor=True)
        best_sentence = torch.argmax(scores).item()

        candidate.representation = []
        if best_sentence > 0:
            prefix = ' '.join(sentences[:best_sentence])
            candidate.representation.append(ResultPresentation(prefix, False))
        candidate.representation.append(ResultPresentation(sentences[best_sentence], True))
        if best_sentence < len(sentences) - 1:
            suffix = ' '.join(sentences[best_sentence + 1:])
            candidate.representation.append(ResultPresentation(suffix, False))

    return candidates


def search_documents(query: str, top_k: int) -> List[dict]:
    # Encode the query
    query_embedding = bi_encoder.encode(query, convert_to_tensor=True)

    # Search the index for 100 candidates
    index = FaissIndex.get()
    results = index.search(query_embedding, BI_ENCODER_CANDIDATES)
    results = results[0]
    results = [int(id) for id in results if id != -1]  # filter out empty results
    # Get the paragraphs from the database
    with Session() as session:
        paragraphs = session.query(Paragraph).filter(Paragraph.id.in_(results)).all()
        if len(paragraphs) == 0:
            return []
        candidates = [Candidate(content=paragraph.content, score=0.0) for paragraph in paragraphs]
        # calculate small cross-encoder scores to leave just a few candidates
        candidates = _cross_encode(cross_encoder_small, query, candidates, SMALL_CROSS_ENCODER_CANDIDATES)
        # calculate large cross-encoder scores to leave just top_k candidates
        candidates = _cross_encode(cross_encoder_large, query, candidates, top_k)
        candidates = _find_answers_in_candidates(candidates, query)
        return [candidate.to_api() for candidate in candidates]
