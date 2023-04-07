from dataclasses import dataclass
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Column, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref

from schemas.base import Base


@dataclass
class Document(Base):
    __tablename__ = 'document'

    id: Mapped[int] = mapped_column(primary_key=True)
    id_in_data_source: Mapped[str] = mapped_column(String(64))
    data_source_id = Column(Integer, ForeignKey('data_source.id'))
    data_source = relationship("DataSource", back_populates="documents")
    type: Mapped[Optional[str]] = mapped_column(String(32))
    file_type: Mapped[Optional[str]] = mapped_column(String(32))
    status: Mapped[Optional[bool]] = mapped_column(String(32))
    title: Mapped[Optional[str]] = mapped_column(String(128))
    author: Mapped[Optional[str]] = mapped_column(String(64))
    author_image_url: Mapped[Optional[str]] = mapped_column(String(512))
    url: Mapped[Optional[str]] = mapped_column(String(512))
    location: Mapped[Optional[str]] = mapped_column(String(512))
    timestamp: Mapped[Optional[DateTime]] = mapped_column(DateTime())
    paragraphs = relationship("Paragraph", back_populates="document", cascade='all, delete, delete-orphan',
                              foreign_keys="Paragraph.document_id")

    parent_id = Column(Integer, ForeignKey('document.id'))
    children = relationship("Document", foreign_keys=[parent_id], backref=backref("parent", remote_side=[id]),
                            cascade='all, delete, delete-orphan', single_parent=True)
