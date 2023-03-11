import logging
from threading import Thread

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from api.search import router as search_router
from data_sources.confluence import ConfluenceDataSource
from data_sources.slack import SlackDataSource
from db_engine import Session
from indexing.background_indexer import BackgroundIndexer
from indexing.bm25_index import Bm25Index
from indexing.faiss_index import FaissIndex
from schemas.document import Document
from schemas.paragraph import Paragraph

app = FastAPI()
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_router)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s')
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_event():
    FaissIndex.create()
    Bm25Index.create()
    Thread(target=BackgroundIndexer.run).start()


@app.post("/index-confluence")
async def index_confluence(background_tasks: BackgroundTasks):
    logger.debug("Start indexing confluence documents")
    confluence = ConfluenceDataSource()
    background_tasks.add_task(confluence.feed_new_documents)


@app.post("/index-slack")
async def index_slack(background_tasks: BackgroundTasks):
    logger.debug("Start indexing slack documents")
    slack = SlackDataSource()
    background_tasks.add_task(slack.feed_new_documents)


@app.post("/clear-index")
async def clear_index():
    FaissIndex.get().clear()
    Bm25Index.get().clear()
    with Session() as session:
        session.query(Document).delete()
        session.query(Paragraph).delete()
        session.commit()
