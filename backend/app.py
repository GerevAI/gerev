import random
import torch
from sentence_transformers import SentenceTransformer
from index import Index

bi_encoder = SentenceTransformer('multi-qa-MiniLM-L6-cos-v1')

def test():
    Index.create()
    new_passage = 'current number is ' + str(random.randint(0, 1000))
    embeddings = bi_encoder.encode([new_passage], convert_to_tensor=True)
    
    Index.get().add_and_save(torch.tensor([2]), embeddings)

    print(Index.get().search(embeddings, 3))
