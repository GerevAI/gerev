import json
from datetime import datetime
import importlib
from typing import List

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from db_engine import Session
from schemas import DataSourceType, DataSource

router = APIRouter(
    prefix='/data-source',
)


@router.get("/list-types")
async def list_data_source_types() -> List[str]:
    with Session() as session:
        data_sources = session.query(DataSourceType).all()
        return [data_source.name for data_source in data_sources]


@router.get("/list-connected")
async def list_connected_data_sources() -> List[str]:
    with Session() as session:
        data_sources = session.query(DataSource).all()
        return [data_source.type.name for data_source in data_sources]


class AddDataSource(BaseModel):
    name: str
    config: dict


@router.post("/add")
async def add_integration(dto: AddDataSource, background_tasks: BackgroundTasks):
    with Session() as session:
        data_source_type = session.query(DataSourceType).filter_by(name=dto.name).first()
        if data_source_type is None:
            return {"error": "Data source type does not exist"}

        data_source_file_name = dto.name
        data_source_class = f"{data_source_file_name.capitalize()}DataSource"
        module = importlib.import_module(f"data_sources.{data_source_file_name}")
        data_source_class = getattr(module, data_source_class)
        data_source_class.validate_config(dto.config)

        config_str = json.dumps(dto.config)
        ds = DataSource(type_id=data_source_type.id, config=config_str, created_at=datetime.now())
        session.add(ds)
        session.commit()

        data_source_id = session.query(DataSource).filter_by(type_id=data_source_type.id)\
            .order_by(DataSource.id.desc()).first().id

        # TODO: remove it, a monitoring background task should do that
        data_source = data_source_class(data_source_id=data_source_id, config=dto.config)
        background_tasks.add_task(data_source.feed_new_documents)

        return {"success": "Data source added successfully"}
