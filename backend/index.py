import os
import faiss


INDEX_PATH = '/tmp/index.bin'
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
        return Index.instance

    def __init__(self) -> None:
        if os.path.exists(INDEX_PATH):
            index = faiss.read_index(INDEX_PATH)
        else:
            index = faiss.IndexFlatIP(MODEL_DIM)
            index = faiss.IndexIDMap(index)

        self.index: faiss.IndexIDMap = index
    
    def add_and_save(self, ids, embeddings):
        self.index.add_with_ids(embeddings, ids)

        faiss.write_index(self.index, INDEX_PATH)

    def search(self, queries, top_k, *args, **kwargs):
        D, I = self.index.search(queries, top_k, *args, **kwargs)
        return I
        



