import logging
from threading import Thread
import os
import json
import torch
import posthog
import uuid

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from data_sources.confluence import ConfluenceDataSource
from data_sources.slack import SlackDataSource
from db_engine import Session
from indexing.background_indexer import BackgroundIndexer
from indexing.bm25_index import Bm25Index
from indexing.faiss_index import FaissIndex
from schemas import DataSource
from schemas.data_source_type import DataSourceType
from schemas.document import Document
from schemas.paragraph import Paragraph
from paths import UI_PATH

from api.search import router as search_router
from api.data_source import router as data_source_router


def telemetry():
    import uuid
    import os

    # Check if TEST environment variable is set
    if os.environ.get('TEST') == "1":
        uuid_path = os.path.join(os.environ['HOME'], '.gerev.uuid')
        with open(uuid_path, 'w') as f:
            f.write("test")
        return

    else:
        uuid_path = os.path.join(os.environ['HOME'], '.gerev.uuid')
        if os.path.exists(uuid_path):
            with open(uuid_path, 'r') as f:
                existing_uuid = f.read().strip()
                
            print(f"Using existing UUID: {existing_uuid}")
            if "test" in existing_uuid:
                print("Skipping telemetry capture due to 'test' UUID")
                return
        else:
            new_uuid = uuid.uuid4()
            print(f"Generated new UUID: {new_uuid}")
            
            with open(uuid_path, 'w') as f:
                f.write(str(new_uuid))

            existing_uuid = new_uuid

            # Capture an event with PostHog
            import posthog
            posthog.api_key = "phc_unIQdP9MFUa5bQNIKy5ktoRCPWMPWgqTbRvZr4391"
            posthog.host = 'https://eu.posthog.com'

            # Identify a user with the UUID
            posthog.identify(str(existing_uuid))

            # Capture an event
            posthog.capture(str(existing_uuid), "run")

telemetry()

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
app.include_router(data_source_router)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s')
logger = logging.getLogger(__name__)


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
    Thread(target=BackgroundIndexer.run).start()


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
except:
    print("Please build UI or comment this")
    raise
