from typing import TYPE_CHECKING
from schemas.document import Document
from schemas.base import Base
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Paragraph(Base):
    __tablename__ = "paragraph"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(String(2048))

    document_id: Mapped[int] = mapped_column(ForeignKey('document.id'))
    document: Mapped[Document] = relationship(back_populates='paragraphs')