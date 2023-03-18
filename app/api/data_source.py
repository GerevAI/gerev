import json
from datetime import datetime
from typing import List

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from data_source_api.utils import get_class_by_data_source_name
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

        data_source_class = get_class_by_data_source_name(dto.name)
        data_source_class.validate_config(dto.config)

        config_str = json.dumps(dto.config)
        ds = DataSource(type_id=data_source_type.id, config=config_str, created_at=datetime.now())
        session.add(ds)
        session.commit()

        data_source_id = session.query(DataSource).filter_by(type_id=data_source_type.id)\
            .order_by(DataSource.id.desc()).first().id
        data_source = data_source_class(config=dto.config, data_source_id=data_source_id)

        # in main.py we have a background task that runs every 5 minutes and indexes the data source
        # but here we want to index the data source immediately
        background_tasks.add_task(data_source.index)

        return {"success": "Data source added successfully"}
