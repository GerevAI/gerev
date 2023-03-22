from schemas import DataSourceType
from schemas import DataSource
from schemas import Document
from schemas import Paragraph

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# import base document and then register all classes
from schemas.base import Base

from paths import SQLITE_DB_PATH

engine = create_engine(f'sqlite:///{SQLITE_DB_PATH}')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
