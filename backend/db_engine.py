import os

from models import Document
from models import Paragraph

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# import base document and then register all classes
from models.base import Base

from sqlalchemy.orm import declarative_base
if not os.path.exists('/tmp/storage/'):
    os.mkdir('/tmp/storage/')
engine = create_engine('sqlite:////tmp/storage/db.sqlite3')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
