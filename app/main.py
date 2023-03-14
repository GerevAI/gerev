import json
import logging
import os
from threading import Thread

import torch
from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import JSONResponse

from api.data_source import router as data_source_router
from api.search import router as search_router
from data_sources.confluence import ConfluenceDataSource
from data_sources.slack import SlackDataSource
from db_engine import Session
from indexing.background_indexer import BackgroundIndexer
from indexing.bm25_index import Bm25Index
from indexing.faiss_index import FaissIndex
from paths import UI_PATH
from schemas import DataSource
from schemas.data_source_type import DataSourceType
from schemas.document import Document
from schemas.paragraph import Paragraph

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(search_router)
app.include_router(data_source_router)


@app.exception_handler(Exception)
def handle_exception_middleware(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": f"Oops! Server error..."},
    )


def load_supported_data_sources_to_db():
    supported_data_source_type = []
    for file in os.listdir("data_sources"):
        if file.endswith(".py") and file != "__init__.py":
            supported_data_source_type.append(file[:-3])

    with Session() as session:
        for data_source_type in supported_data_source_type:
            if session.query(DataSourceType).filter_by(name=data_source_type).first():
                continue

            new_data_source = DataSourceType(name=data_source_type)
            session.add(new_data_source)
            session.commit()


@app.on_event("startup")
async def startup_event():
    if not torch.cuda.is_available():
        logger.warning("CUDA is not available, using CPU. This will make indexing and search very slow!!!")
    FaissIndex.create()
    Bm25Index.create()
    load_supported_data_sources_to_db()
    BackgroundIndexer.start()


@app.on_event("shutdown")
async def shutdown_event():
    BackgroundIndexer.stop()


@app.post("/index-confluence")
async def index_confluence(background_tasks: BackgroundTasks):
    # TODO: temporary solution, will be added thru api
    logger.debug("Start indexing confluence documents")
    confluence_config = {"token": os.environ.get("CONFLUENCE_TOKEN"),
                         "url": os.environ.get("CONFLUENCE_URL")}
    confluence_json = json.dumps(confluence_config)

    # make data_source row
    ds = DataSource(type_id=2, config=confluence_json)
    with Session() as session:
        session.add(ds)
        session.commit()

    # get data_source row
    with Session() as session:
        confluence_data_source = session.query(DataSource).filter_by(type_id=2).first()

    confluence = ConfluenceDataSource(data_source_id=confluence_data_source.id, config=confluence_config)
    background_tasks.add_task(confluence.feed_new_documents)


@app.post("/index-slack")
async def index_slack(background_tasks: BackgroundTasks):
    # TODO: temporary solution, will be added thru api
    logger.debug("Start indexing slack documents")
    slack_config = {"token": os.environ.get("SLACK_TOKEN")}
    slack_json = json.dumps(slack_config)

    # make data_source row
    ds = DataSource(type_id=1, config=slack_json)
    with Session() as session:
        session.add(ds)
        session.commit()

    # get data_source row
    with Session() as session:
        slack_data_source = session.query(DataSource).filter_by(type_id=1).first()

    slack = SlackDataSource(data_source_id=slack_data_source.id, config=slack_config)
    background_tasks.add_task(slack.feed_new_documents)


@app.post("/clear-index")
async def clear_index():
    FaissIndex.get().clear()
    Bm25Index.get().clear()
    with Session() as session:
        session.query(Document).delete()
        session.query(Paragraph).delete()
        session.commit()


try:
    app.mount('/', StaticFiles(directory=UI_PATH, html=True), name='ui')
except Exception as e:
    logger.warning(f"Failed to mount UI (you probably need to build it): {e}")
