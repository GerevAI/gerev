import base64
import json
from datetime import datetime
from typing import List

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from starlette.responses import Response

from data_source_api.base_data_source import ConfigField
from data_source_api.exception import KnownException
from data_source_api.utils import get_class_by_data_source_name
from db_engine import Session
from schemas import DataSourceType, DataSource

router = APIRouter(
    prefix='/data-source',
)


class DataSourceTypeDto(BaseModel):
    name: str
    display_name: str
    config_fields: List[ConfigField]
    image_base64: str

    @staticmethod
    def from_data_source_type(data_source_type: DataSourceType) -> 'DataSourceTypeDto':
        with open(f"static/data_source_icons/{data_source_type.name}.png", "rb") as file:
            encoded_string = base64.b64encode(file.read())
            image_base64 = f"data:image/png;base64,{encoded_string.decode()}"

        config_fields_json = json.loads(data_source_type.config_fields)
        return DataSourceTypeDto(
            name=data_source_type.name,
            display_name=data_source_type.display_name,
            config_fields=[ConfigField(**config_field) for config_field in config_fields_json],
            image_base64=image_base64
        )


@router.get("/list-types")
async def list_data_source_types() -> List[DataSourceTypeDto]:
    with Session() as session:
        data_source_types = session.query(DataSourceType).all()
        return [DataSourceTypeDto.from_data_source_type(data_source_type)
                for data_source_type in data_source_types]


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
        try:
            data_source_class.validate_config(dto.config)
        except KnownException as e:
            return Response(e.message, status_code=501)

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
