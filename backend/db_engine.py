from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///storage/db.sqlite3')
Session = sessionmaker(bind=engine)
