from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from models.document import Document
from models.base import Base
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Paragraph(Base):
    __tablename__ = "paragraph"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(String(2048))

    document: Mapped['Document'] = relationship(back_populates='paragraphs')