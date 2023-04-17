import logging
from typing import Optional

from schemas.base import Base
from sqlalchemy import ForeignKey, Column, Integer, Connection
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime
from sqlalchemy import event


logger = logging.getLogger(__name__)


class DataSource(Base):
    __tablename__ = "data_source"

    id: Mapped[int] = mapped_column(primary_key=True)
    type_id = Column(Integer, ForeignKey('data_source_type.id'))
    type = relationship("DataSourceType", back_populates="data_sources")
    config: Mapped[Optional[str]] = mapped_column(String(512))
    last_indexed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime())
    created_at: Mapped[Optional[DateTime]] = mapped_column(DateTime())
    documents = relationship("Document", back_populates="data_source", cascade='all, delete, delete-orphan')


@event.listens_for(DataSource, 'before_delete')
def receive_before_delete(mapper, connection: Connection, target):
    # import here to avoid circular imports
    from indexing.index_documents import Indexer
    from db_engine import Session

    with Session(bind=connection) as session:
        logger.info(f"Deleting documents for data source {target.id}...")
        Indexer.remove_documents(target.documents, session=session)
