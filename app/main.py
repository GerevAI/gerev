import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List

import torch
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_restful.tasks import repeat_every
from starlette.responses import Response

from api.data_source import router as data_source_router
from api.search import router as search_router
from data_source_api.exception import KnownException
from data_source_api.utils import get_class_by_data_source_name
from db_engine import Session
from indexing.background_indexer import BackgroundIndexer
from indexing.bm25_index import Bm25Index
from indexing.faiss_index import FaissIndex
from indexing_queue import IndexingQueue
from paths import UI_PATH
from schemas import DataSource
from schemas.data_source_type import DataSourceType
from schemas.document import Document
from schemas.paragraph import Paragraph
from telemetry import Posthog

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()


async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except KnownException as e:
        logger.exception("Known exception")
        return Response(e.message, status_code=501)
    except Exception:
        logger.exception("Server error")
        return Response("Oops. Server error...", status_code=500)

app.middleware('http')(catch_exceptions_middleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(search_router)
app.include_router(data_source_router)


@app.on_event("startup")
@repeat_every(seconds=60)
def check_for_new_documents():
    with Session() as session:
        data_sources: List[DataSource] = session.query(DataSource).all()
        for data_source in data_sources:
            # data source should be checked once every hour
            if (datetime.now() - data_source.last_indexed_at).total_seconds() <= 60 * 60:
                continue

            logger.info(f"Checking for new docs in {data_source.type.name} (id: {data_source.id})")
            data_source_cls = get_class_by_data_source_name(data_source.type.name)
            config = json.loads(data_source.config)
            data_source_instance = data_source_cls(config=config, data_source_id=data_source.id,
                                                   last_index_time=data_source.last_indexed_at)
            data_source_instance.index()


@app.on_event("startup")
def send_startup_telemetry():
    try:
        Posthog.send_startup_telemetry()
    except:
        logging.exception("Failed to send startup telemetry")


@app.on_event("startup")
@repeat_every(wait_first=60 * 60 * 24, seconds=60 * 60 * 24)
def send_daily_telemetry():
    try:
        Posthog.send_daily()
    except:
        logger.exception("Failed to send daily telemetry")


def load_data_source_types():
    supported_data_source_type = []
    for file in os.listdir("data_sources"):
        if file.endswith(".py") and file != "__init__.py":
            supported_data_source_type.append(file[:-3])

    with Session() as session:
        for data_source_type in supported_data_source_type:
            if session.query(DataSourceType).filter_by(name=data_source_type).first():
                continue

            data_source_class = get_class_by_data_source_name(data_source_type)
            config_fields = data_source_class.get_config_fields()
            config_fields_str = json.dumps([config_field.dict() for config_field in config_fields])
            new_data_source = DataSourceType(name=data_source_type,
                                             display_name=data_source_class.get_display_name(),
                                             config_fields=config_fields_str)
            session.add(new_data_source)
            session.commit()


@app.on_event("startup")
async def startup_event():
    if not torch.cuda.is_available():
        logger.warning("CUDA is not available, using CPU. This will make indexing and search very slow!!!")
    FaissIndex.create()
    Bm25Index.create()
    load_data_source_types()
    BackgroundIndexer.start()


@app.on_event("shutdown")
async def shutdown_event():
    BackgroundIndexer.stop()


@app.get("/status")
async def status():
    @dataclass
    class Status:
        docs_in_indexing: int
        docs_left_to_index: int

    return Status(docs_in_indexing=BackgroundIndexer.get_currently_indexing(),
                  docs_left_to_index=IndexingQueue.get().get_how_many_left())


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


# if __name__ == '__main__':
#     import uvicorn
#     uvicorn.run(app, host="localhost", port=8000)
