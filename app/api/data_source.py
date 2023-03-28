import base64
import json
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel
from starlette.background import BackgroundTasks
from starlette.requests import Request

from data_source.api.base_data_source import ConfigField
from data_source.api.context import DataSourceContext
from db_engine import Session
from schemas import DataSourceType, DataSource
from telemetry import Posthog

router = APIRouter(
    prefix='/data-sources',
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


class ConnectedDataSourceDto(BaseModel):
    id: int
    name: str


@router.get("/types")
async def list_data_source_types() -> List[DataSourceTypeDto]:
    with Session() as session:
        data_source_types = session.query(DataSourceType).all()
        return [DataSourceTypeDto.from_data_source_type(data_source_type)
                for data_source_type in data_source_types]


@router.get("/connected")
async def list_connected_data_sources() -> List[ConnectedDataSourceDto]:
    with Session() as session:
        data_sources = session.query(DataSource).all()
        return [ConnectedDataSourceDto(id=data_source.id, name=data_source.type.name)
                for data_source in data_sources]


class AddDataSource(BaseModel):
    name: str
    config: dict


@router.delete("/{data_source_id}")
async def delete_data_source(request: Request, data_source_id: int):
    deleted_name = DataSourceContext.delete_data_source(data_source_id=data_source_id)
    Posthog.removed_data_source(uuid=request.headers.get('uuid'), name=deleted_name)
    return {"success": "Data source deleted successfully"}


@router.post("")
async def add_integration(request: Request, dto: AddDataSource, background_tasks: BackgroundTasks) -> int:
    data_source = DataSourceContext.create_data_source(name=dto.name, config=dto.config)
    Posthog.added_data_source(uuid=request.headers.get('uuid'), name=dto.name)
    # in main.py we have a background task that runs every 5 minutes and indexes the data source
    # but here we want to index the data source immediately
    background_tasks.add_task(data_source.index)

    return data_source.get_id()
