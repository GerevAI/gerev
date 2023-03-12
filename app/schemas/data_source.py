from typing import Optional

from schemas.base import Base
from sqlalchemy import ForeignKey, Column, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime


class DataSource(Base):
    __tablename__ = "data_source"

    id: Mapped[int] = mapped_column(primary_key=True)
    type_id = Column(Integer, ForeignKey('data_source_type.id'))
    type = relationship("DataSourceType", back_populates="data_sources")
    config: Mapped[Optional[str]] = mapped_column(String(512))
    last_indexed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime())
    created_at: Mapped[Optional[DateTime]] = mapped_column(DateTime())
    documents = relationship("Document", back_populates="data_source")
