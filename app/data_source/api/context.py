import json
import logging
from dataclasses import dataclass
from typing import Dict, List

from pydantic import ValidationError
from sqlalchemy import select

from data_source.api.base_data_source import BaseDataSource
from data_source.api.dynamic_loader import DynamicLoader, ClassInfo
from data_source.api.exception import KnownException
from data_source.api.utils import get_utc_time_now
from db_engine import Session, async_session
from schemas import DataSourceType, DataSource, Document

logger = logging.getLogger(__name__)


@dataclass
class CachedDataSource:
    indexed_docs: int
    failed_tasks: int
    instance: BaseDataSource


class DataSourceContext:
    """
    This class is responsible for loading data sources and caching them.
    It dynamically loads data source types from the data_source/sources directory.
    It loads data sources from the database and caches them.
    """
    _initialized = False
    _data_source_cache: Dict[int, CachedDataSource] = {}
    _data_source_classes: Dict[str, BaseDataSource] = {}

    @classmethod
    def get_data_source_instance(cls, data_source_id: int) -> BaseDataSource:
        if not cls._initialized:
            cls.init()
            cls._initialized = True

        return cls._data_source_cache[data_source_id].instance

    @classmethod
    def get_data_source_class(cls, data_source_name: str) -> BaseDataSource:
        if not cls._initialized:
            cls.init()
            cls._initialized = True

        return cls._data_source_classes[data_source_name]

    @classmethod
    def get_data_source_classes(cls) -> Dict[str, BaseDataSource]:
        if not cls._initialized:
            cls.init()
            cls._initialized = True

        return cls._data_source_classes

    @classmethod
    async def create_data_source(cls, name: str, config: dict) -> BaseDataSource:
        async with async_session() as session:
            data_source_type = await session.execute(
                select(DataSourceType).filter_by(name=name)
            )
            data_source_type = data_source_type.scalar_one_or_none()
            if data_source_type is None:
                raise KnownException(message=f"Data source type {name} does not exist")

            data_source_class = DynamicLoader.get_data_source_class(name)
            logger.info(f"validating config for data source {name}")
            await data_source_class.validate_config(config)
            config_str = json.dumps(config)

            data_source_row = DataSource(type_id=data_source_type.id, config=config_str, created_at=get_utc_time_now())
            session.add(data_source_row)
            await session.commit()

            data_source = data_source_class(config=config, data_source_id=data_source_row.id)
            cls._data_source_cache[data_source_row.id] = CachedDataSource(indexed_docs=0, failed_tasks=0,
                                                                          instance=data_source)

            return data_source

    @classmethod
    def delete_data_source(cls, data_source_id: int) -> str:
        with Session() as session:
            data_source = session.query(DataSource).filter_by(id=data_source_id).first()
            if data_source is None:
                raise KnownException(message=f"Data source {data_source_id} does not exist")

            data_source_name = data_source.type.name
            logger.info(f"Deleting data source {data_source_id} ({data_source_name})...")
            session.delete(data_source)
            session.commit()

            del cls._data_source_cache[data_source_id]

            return data_source_name

    @classmethod
    def init(cls):
        cls._load_data_source_classes()
        cls._load_connected_sources_from_db()

    @classmethod
    def _load_connected_sources_from_db(cls):
        logger.info("Loading data sources from database")

        with Session() as session:
            data_sources: List[DataSource] = session.query(DataSource).all()
            for data_source in data_sources:
                logger.info(f"Loading data source {data_source.id} ({data_source.type.name})")
                data_source_cls = DynamicLoader.get_data_source_class(data_source.type.name)
                config = json.loads(data_source.config)
                try:
                    data_source_instance = data_source_cls(config=config, data_source_id=data_source.id,
                                                           last_index_time=data_source.last_indexed_at)
                except ValidationError as e:
                    logger.error(f"Error loading data source {data_source.id}: {e}")
                    return

                cached_data_source = CachedDataSource(indexed_docs=len(data_source.documents),
                                                      failed_tasks=0,
                                                      instance=data_source_instance)
                cls._data_source_cache[data_source.id] = cached_data_source
                logger.info(f"Loaded data source {data_source.id} ({data_source.type.name})")

        cls._initialized = True

    @classmethod
    def _load_data_source_classes(cls):
        data_sources: Dict[str, ClassInfo] = DynamicLoader.find_data_sources()

        with Session() as session:
            for source_name in data_sources.keys():
                class_info = data_sources[source_name]
                data_source_class = DynamicLoader.get_class(file_path=class_info.file_path,
                                                            class_name=class_info.name)
                cls._data_source_classes[source_name] = data_source_class

                if session.query(DataSourceType).filter_by(name=source_name).first():
                    continue

                config_fields = data_source_class.get_config_fields()
                config_fields_str = json.dumps([config_field.dict() for config_field in config_fields])
                new_data_source = DataSourceType(name=source_name,
                                                 display_name=data_source_class.get_display_name(),
                                                 config_fields=config_fields_str)
                session.add(new_data_source)
                session.commit()
