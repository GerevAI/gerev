import os
import pickle
import nltk
import numpy as np
from rank_bm25 import BM25Okapi
from typing import List

from db_engine import Session
from schemas import Paragraph

INDEX_PATH = '/tmp/storage/bm25_index.bin'


class Bm25Index:
    instance = None

    @staticmethod
    def create():
        if Bm25Index.instance is not None:
            raise RuntimeError("Index is already initialized")

        if os.path.exists(INDEX_PATH):
            with open(INDEX_PATH, 'rb') as f:
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

    def update(self):
        with Session() as session:
            all_paragraphs = session.query(Paragraph).all()
            corpus = [nltk.word_tokenize(paragraph.content) for paragraph in all_paragraphs]
            id_map = [paragraph.id for paragraph in all_paragraphs]
            self.index = BM25Okapi(corpus)
            self.id_map = id_map
        self._save()

    def search(self, query: str, top_k: int) -> List[int]:
        tokenized_query = nltk.word_tokenize(query)
        bm25_scores = self.index.get_scores(tokenized_query)
        top_n = np.argpartition(bm25_scores, -top_k)[-top_k:]
        bm25_hits = [{'id': self.id_map[idx], 'score': bm25_scores[idx]} for idx in top_n]
        bm25_hits = sorted(bm25_hits, key=lambda x: x['score'], reverse=True)
        return [hit['id'] for hit in bm25_hits]

    def clear(self):
        self.index = None
        self.id_map = []
        self._save()

    def _save(self):
        with open(INDEX_PATH, 'wb') as f:
            pickle.dump(self, f)