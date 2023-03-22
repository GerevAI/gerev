import base64
import datetime
import json
import logging

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from io import BytesIO
from typing import List
from typing import Optional
import re
import nltk
import requests
import torch
import urllib.parse
from sentence_transformers import CrossEncoder

from db_engine import Session
from indexing.bm25_index import Bm25Index
from indexing.faiss_index import FaissIndex
from data_source_api.basic_document import DocumentType, FileType
from models import bi_encoder, cross_encoder_small, cross_encoder_large, qa_model
from schemas import Paragraph, Document

BM_25_CANDIDATES = 100 if torch.cuda.is_available() else 20
BI_ENCODER_CANDIDATES = 60 if torch.cuda.is_available() else 20
SMALL_CROSS_ENCODER_CANDIDATES = 30 if torch.cuda.is_available() else 10

nltk.download('punkt')


@dataclass
class TextPart:
    content: str
    bold: bool


@dataclass
class SearchResult:
    type: DocumentType
    score: float
    content: List[TextPart]
    author: str
    title: str
    url: str
    location: str
    data_source: str
    time: datetime
    file_type: FileType
    author_image_url: Optional[str]
    author_image_data: Optional[str]


@dataclass
class Candidate:
    content: str
    score: float = 0.0
    document: Document = None
    answer_start: int = -1
    answer_end: int = -1

    def _text_anchor(self, url, text) -> str:
        if '#' not in url:
            url += '#'
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        words = text.split()
        url += ':~:text='
        if len(words) > 7:
            url += urllib.parse.quote(' '.join(words[:3])).replace('-', '%2D')
            url += ','
            url += urllib.parse.quote(' '.join(words[-3:])).replace('-', '%2D')
        else:
            url += urllib.parse.quote(text).replace('-', '%2D')
        return url

    def to_search_result(self) -> SearchResult:
        answer = TextPart(self.content[self.answer_start: self.answer_end], True)
        content = [answer]

        if self.answer_end < len(self.content) - 1:
            words = self.content[self.answer_end:].split()
            suffix = ' '.join(words[:20])
            content.append(TextPart(suffix, False))

        data_uri = None
        if self.document.data_source.type.name == 'confluence':
            url = self.document.author_image_url
            if "anonymous.svg" in url:
                url = url.replace(".svg", ".png")

            config = json.loads(self.document.data_source.config)
            response = requests.get(url=url, headers={'Accept': 'application/json',
                                                      "Authorization": f"Bearer {config['token']}"})
            image_bytes = BytesIO(response.content)
            data_uri = f"data:image/jpeg;base64,{base64.b64encode(image_bytes.getvalue()).decode()}"

        return SearchResult(score=(self.score + 12) / 24 * 100,
                            content=content,
                            author=self.document.author,
                            author_image_url=self.document.author_image_url,
                            author_image_data=data_uri,
                            title=self.document.title,
                            url=self._text_anchor(self.document.url, answer.content),
                            time=self.document.timestamp,
                            location=self.document.location,
                            data_source=self.document.data_source.type.name,
                            type=self.document.type,
                            file_type=self.document.file_type)


def _cross_encode(
        cross_encoder: CrossEncoder,
        query: str,
        candidates: List[Candidate],
        top_k: int,
        use_answer: bool = False,
        use_titles: bool = False) -> List[Candidate]:
    if use_answer:
        contents = [candidate.content[candidate.answer_start:candidate.answer_end] for candidate in candidates]
    else:
        contents = [candidate.content for candidate in candidates]
    
    if use_titles:
        contents = [
            content + ' [SEP] ' + candidate.document.title
            for content, candidate in zip(contents, candidates)
        ]

    scores = cross_encoder.predict([(query, content) for content in contents], show_progress_bar=False)
    for candidate, score in zip(candidates, scores):
        candidate.score = score.item()
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:top_k]


def _assign_answer_sentence(candidate: Candidate, answer: str):
    paragraph_sentences = re.split(r'([\.\!\?\:\-] |[\"“\(\)])', candidate.content)
    sentence = None
    for i, paragraph_sentence in enumerate(paragraph_sentences):
        if answer in paragraph_sentence:
            sentence = paragraph_sentence
            break
    else:
        sentence = answer
    start = candidate.content.find(sentence)
    end = start + len(sentence)
    candidate.answer_start = start
    candidate.answer_end = end


def _find_answers_in_candidates(candidates: List[Candidate], query: str) -> List[Candidate]:
    contexts = [candidate.content for candidate in candidates]
    answers = qa_model(question=[query] * len(contexts), context=contexts)
    for candidate, answer in zip(candidates, answers):
        _assign_answer_sentence(candidate, answer['answer'])

    return candidates


def search_documents(query: str, top_k: int) -> List[SearchResult]:
    # Encode the query
    query_embedding = bi_encoder.encode(query, convert_to_tensor=True, show_progress_bar=False)

    # Search the index for 100 candidates
    index = FaissIndex.get()
    results = index.search(query_embedding, BI_ENCODER_CANDIDATES)
    results = results[0]
    results = [int(id) for id in results if id != -1]  # filter out empty results

    results += Bm25Index.get().search(query, BM_25_CANDIDATES)
    # Get the paragraphs from the database
    with Session() as session:
        paragraphs = session.query(Paragraph).filter(Paragraph.id.in_(results)).all()
        if len(paragraphs) == 0:
            return []
        candidates = [Candidate(content=paragraph.content, document=paragraph.document, score=0.0)
                      for paragraph in paragraphs]

        # calculate small cross-encoder scores to leave just a few candidates
        logger = logging.getLogger('search')
        logger.info(f'Found {len(candidates)} candidates, filtering...')
        candidates = _cross_encode(cross_encoder_small, query, candidates, BI_ENCODER_CANDIDATES, use_titles=True)
        # calculate large cross-encoder scores to leave just top_k candidates
        candidates = _cross_encode(cross_encoder_large, query, candidates, top_k, use_titles=True)
        candidates = _find_answers_in_candidates(candidates, query)
        candidates = _cross_encode(cross_encoder_large, query, candidates, top_k, use_answer=True, use_titles=True)

        logger.info(f'Parsing {len(candidates)} candidates to search results...')

        with ThreadPoolExecutor(max_workers=10) as executor:
            result = list(executor.map(lambda c: c.to_search_result(), candidates))
            return result
