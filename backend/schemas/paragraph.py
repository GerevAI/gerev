from schemas.base import Base
from sqlalchemy import String, ForeignKey, Column, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Paragraph(Base):
    __tablename__ = "paragraph"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(String(2048))

    document_id = Column(Integer, ForeignKey('document.id'))
    document = relationship("Document", back_populates="paragraphs")
