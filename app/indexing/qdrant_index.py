import torch

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, Batch
import qdrant_client.http.exceptions as qdrant_exceptions

MODEL_DIM = 384


class QdrantIndex:
    instance = None

    @staticmethod
    def create():
        if QdrantIndex.instance is not None:
            raise RuntimeError("Index is already initialized")

        QdrantIndex.instance = QdrantIndex()

    @staticmethod
    def get() -> 'QdrantIndex':
        if QdrantIndex.instance is None:
            raise RuntimeError("Index is not initialized")
        return QdrantIndex.instance

    def __init__(self) -> None:
        self.collection_name = 'paragraphs'
        self.client = QdrantClient(host='localhost', port=6333)

        self._create_collection_if_not_exists()

    def _create_collection_if_not_exists(self):
        try:
            self.collection = self.client.get_collection(self.collection_name)
        except qdrant_exceptions.UnexpectedResponse as e:
            if e.status_code != 404:
                raise
            
            self.collection = self.client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=MODEL_DIM,
                    distance=Distance.COSINE
                )
            )

    def update(self, ids: list, embeddings: torch.FloatTensor):
        if isinstance(embeddings, torch.Tensor):
            embeddings = embeddings.tolist()

        if not len(ids) == len(embeddings):
            raise ValueError('Ids and embeddings must have the same length')
        
        batch_size = 500
        for i in range(0, len(ids), batch_size):
            self.client.upsert(
                collection_name=self.collection_name,
                points=Batch(
                    ids=ids[i:i + batch_size],
                    vectors=embeddings[i:i + batch_size]
                )
            )

    def search(self, query: torch.FloatTensor, top_k: int):
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query.tolist(),
            limit=top_k
        )
        return [[result.id for result in results]]

    def clear(self):
        self.client.delete_collection(self.collection_name)
        self._create_collection_if_not_exists()
