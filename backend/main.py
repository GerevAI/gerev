from fastapi import FastAPI, BackgroundTasks

from data_sources.confluence import ConfluenceDataSource
from search import search_documents
from indexing import index_documents
from indexing.faiss_index import FaissIndex
from indexing.bm25_index import Bm25Index
from db_engine import Session
from schemas.document import Document
from schemas.paragraph import Paragraph
from fastapi.middleware.cors import CORSMiddleware
import logging

app = FastAPI()
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# init logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_event():
    FaissIndex.create()
    Bm25Index.create()


@app.post("/example-index")
async def example_index(background_tasks: BackgroundTasks):
    from integrations_api.basic_document import BasicDocument
    from datetime import datetime
    import requests
    logger.debug("Start indexing example documents")
    url = "https://raw.githubusercontent.com/amephraim/nlp/master/texts/J.%20K.%20Rowling%20-%20Harry%20Potter%201%20-%20Sorcerer's%20Stone.txt"
    text = requests.get(url).text
    document1 = BasicDocument(title="Harry potter and the philosopher's stone", content=text, author="J. K. Rowling",
                              timestamp=datetime.now(), id=1, integration_name="confluence", url=url)
    background_tasks.add_task(index_documents, [document1])


@app.post("/index-confluence")
async def index_confluence(background_tasks: BackgroundTasks):
    logger.debug("Start indexing example documents")
    confluence = ConfluenceDataSource()
    docs = confluence.get_documents()
    background_tasks.add_task(index_documents, docs)


@app.post("/clear-index")
async def clear_index():
    FaissIndex.get().clear()
    Bm25Index.get().clear()
    with Session() as session:
        session.query(Document).delete()
        session.query(Paragraph).delete()
        session.commit()


@app.get("/search")
async def search(query: str, top_k: int = 5):
    return search_documents(query, top_k)


@app.get("/")
async def root():
    return {"message": "Hello World"}
