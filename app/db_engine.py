from schemas import DataSourceType
from schemas import DataSource
from schemas import Document
from schemas import Paragraph

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# import base document and then register all classes
from schemas.base import Base

from paths import SQLITE_DB_PATH

db_url = f'sqlite:///{SQLITE_DB_PATH}'
print('DB engine path:', db_url)
engine = create_engine(db_url)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

async_db_url = db_url.replace('sqlite', 'sqlite+aiosqlite', 1)
print('ASYNC DB engine path:', async_db_url)
async_engine = create_async_engine(async_db_url)
async_session = sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)
