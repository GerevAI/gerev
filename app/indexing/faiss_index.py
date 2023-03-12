import os
import torch
import faiss

from paths import FAISS_INDEX_PATH

MODEL_DIM = 384


class FaissIndex:
    instance = None

    @staticmethod
    def create():
        if FaissIndex.instance is not None:
            raise RuntimeError("Index is already initialized")

        FaissIndex.instance = FaissIndex()

    @staticmethod
    def get() -> 'FaissIndex':
        if FaissIndex.instance is None:
            raise RuntimeError("Index is not initialized")
        return FaissIndex.instance

    def __init__(self) -> None:
        if os.path.exists(FAISS_INDEX_PATH):
            index = faiss.read_index(FAISS_INDEX_PATH)
        else:
            index = faiss.IndexFlatIP(MODEL_DIM)
            index = faiss.IndexIDMap(index)

        self.index: faiss.IndexIDMap = index

    def update(self, ids: torch.LongTensor, embeddings: torch.FloatTensor):
        self.index.add_with_ids(embeddings.cpu(), ids)

        faiss.write_index(self.index, FAISS_INDEX_PATH)

    def search(self, queries: torch.FloatTensor, top_k: int, *args, **kwargs):
        if queries.ndim == 1:
            queries = queries.unsqueeze(0)
        _, ids = self.index.search(queries.cpu(), top_k, *args, **kwargs)
        return ids

    def clear(self):
        self.index.reset()
        faiss.write_index(self.index, FAISS_INDEX_PATH)
