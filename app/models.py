from sentence_transformers import SentenceTransformer, CrossEncoder
from transformers import pipeline
import torch


bi_encoder = SentenceTransformer('multi-qa-MiniLM-L6-cos-v1')

cross_encoder_small = CrossEncoder('cross-encoder/ms-marco-TinyBERT-L-2-v2')
cross_encoder_large = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

qa_model = pipeline('question-answering', model='deepset/roberta-base-squad2')
