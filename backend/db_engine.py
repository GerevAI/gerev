import os

from schemas import Document
from schemas import Paragraph

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# import base document and then register all classes
from schemas.base import Base

if not os.path.exists('/tmp/storage/'):
    os.mkdir('/tmp/storage/')
engine = create_engine('sqlite:////tmp/storage/db.sqlite3')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
