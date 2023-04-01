import os
import pickle
from typing import List

import nltk
import numpy as np
from rank_bm25 import BM25Okapi

from db_engine import Session
from paths import BM25_INDEX_PATH
from schemas import Paragraph


def _add_metadata_for_indexing(paragraph: Paragraph) -> str:
    result = paragraph.content
    if paragraph.document.title is not None:
        result += ' ' + paragraph.document.title
    if paragraph.document.author is not None:
        result += ' ' + paragraph.document.author
    if data_source_name := paragraph.document.data_source.type.name:
        result += ' ' + data_source_name
    return result


class Bm25Index:
    instance = None

    @staticmethod
    def create():
        if Bm25Index.instance is not None:
            raise RuntimeError("Index is already initialized")

        if os.path.exists(BM25_INDEX_PATH):
            with open(BM25_INDEX_PATH, 'rb') as f:
                Bm25Index.instance = pickle.load(f)
        else:
            Bm25Index.instance = Bm25Index()

    @staticmethod
    def get() -> 'Bm25Index':
        if Bm25Index.instance is None:
            raise RuntimeError("Index is not initialized")
        return Bm25Index.instance

    def __init__(self) -> None:
        self.index = None
        self.id_map = []

    def _update(self, session):
        all_paragraphs = session.query(Paragraph).all()
        if len(all_paragraphs) == 0:
            self.index = None
            self.id_map = []
            return

        corpus = [nltk.word_tokenize(_add_metadata_for_indexing(paragraph)) for paragraph in all_paragraphs]
        id_map = [paragraph.id for paragraph in all_paragraphs]
        self.index = BM25Okapi(corpus)
        self.id_map = id_map

    def update(self, session=None):
        if session is None:
            with Session() as session:
                self._update(session)
        else:
            self._update(session)

        self._save()

    def search(self, query: str, top_k: int) -> List[int]:
        if self.index is None:
            return []
        tokenized_query = nltk.word_tokenize(query)
        bm25_scores = self.index.get_scores(tokenized_query)
        top_k = min(top_k, len(bm25_scores))
        top_n = np.argpartition(bm25_scores, -top_k)[-top_k:]
        bm25_hits = [{'id': self.id_map[idx], 'score': bm25_scores[idx]} for idx in top_n]
        bm25_hits = sorted(bm25_hits, key=lambda x: x['score'], reverse=True)
        return [hit['id'] for hit in bm25_hits]

    def clear(self):
        self.index = None
        self.id_map = []
        self._save()

    def _save(self):
        with open(BM25_INDEX_PATH, 'wb') as f:
            pickle.dump(self, f)
