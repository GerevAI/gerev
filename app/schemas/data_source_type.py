from schemas.base import Base
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class DataSourceType(Base):
    __tablename__ = 'data_source_type'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32))
    display_name: Mapped[str] = mapped_column(String(32))
    config_fields: Mapped[str] = mapped_column(String(1024))
    data_sources = relationship("DataSource", back_populates="type", foreign_keys="DataSource.type_id")
