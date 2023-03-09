from typing import TYPE_CHECKING, List, Optional
if TYPE_CHECKING:
    from schemas.paragraph import Paragraph
from schemas.base import Base
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Document(Base):
    __tablename__ = 'document'

    id: Mapped[int] = mapped_column(primary_key=True)
    integration_name: Mapped[str] = mapped_column(String(32))
    integration_id: Mapped[int]
    type: Mapped[Optional[str]] = mapped_column(String(32))
    title: Mapped[Optional[str]] = mapped_column(String(128))
    author: Mapped[Optional[str]] = mapped_column(String(64))
    url: Mapped[Optional[str]] = mapped_column(String(512))
    location: Mapped[Optional[str]] = mapped_column(String(512))
    timestamp: Mapped[Optional[DateTime]] = mapped_column(DateTime())
    paragraphs: Mapped[List['Paragraph']] = relationship(
        back_populates='document',
        cascade='all, delete-orphan'
    )
