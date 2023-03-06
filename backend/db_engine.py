from models import Document
from models import Paragraph

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
#import base document and then register all classes
from models.base import Base

from sqlalchemy.orm import declarative_base

engine = create_engine('sqlite:////storage/db.sqlite3')
declarative_base().metadata.create_all(engine)
Session = sessionmaker(bind=engine)
