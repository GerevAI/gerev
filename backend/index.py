import os
import torch
import faiss
from typing import List


INDEX_PATH = '/tmp/storage/index.bin'
MODEL_DIM = 384


class Index():
    instance = None

    @staticmethod
    def create():
        if Index.instance is not None:
            raise RuntimeError("Index is already initialized")

        Index.instance = Index()

    @staticmethod
    def get() -> 'Index':
        if Index.instance is None:
            raise RuntimeError("Index is not initialized")
        return Index.instance

    def __init__(self) -> None:
        if os.path.exists(INDEX_PATH):
            index = faiss.read_index(INDEX_PATH)
        else:
            index = faiss.IndexFlatIP(MODEL_DIM)
            index = faiss.IndexIDMap(index)

        self.index: faiss.IndexIDMap = index

    def update(self, ids: torch.LongTensor, embeddings: torch.FloatTensor):
        self.index.add_with_ids(embeddings, ids)

        faiss.write_index(self.index, INDEX_PATH)

    def search(self, queries: torch.FloatTensor, top_k: int, *args, **kwargs):
        if queries.ndim == 1:
            queries = queries.unsqueeze(0)
        _, ids = self.index.search(queries, top_k, *args, **kwargs)
        return ids

    def clear(self):
        self.index.reset()
        faiss.write_index(self.index, INDEX_PATH)
