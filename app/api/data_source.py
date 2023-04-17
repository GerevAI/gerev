import base64
import json
import logging
import os.path
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel
from starlette.background import BackgroundTasks
from starlette.requests import Request

from data_source.api.base_data_source import ConfigField, BaseDataSource, Location
from data_source.api.context import DataSourceContext
from db_engine import Session
from indexing.background_indexer import BackgroundIndexer
from schemas import DataSource
from telemetry import Posthog

router = APIRouter(
    prefix='/data-sources',
)

logger = logging.getLogger(__name__)


class DataSourceTypeDto(BaseModel):
    name: str
    display_name: str
    config_fields: List[ConfigField]
    image_base64: str
    has_prerequisites: bool

    @staticmethod
    def from_data_source_class(name: str, data_source_class: BaseDataSource) -> 'DataSourceTypeDto':
        icon_path_template = "static/data_source_icons/{name}.png"
        data_source_icon = icon_path_template.format(name=name)
        
        if not os.path.exists(data_source_icon):
            data_source_icon = icon_path_template.format(name="default_icon")
        
        with open(data_source_icon, "rb") as file:
            encoded_string = base64.b64encode(file.read())
            image_base64 = f"data:image/png;base64,{encoded_string.decode()}"

        return DataSourceTypeDto(
            name=name,
            display_name=data_source_class.get_display_name(),
            config_fields=data_source_class.get_config_fields(),
            image_base64=image_base64,
            has_prerequisites=data_source_class.has_prerequisites()
        )


class ConnectedDataSourceDto(BaseModel):
    id: int
    name: str


class AddDataSourceDto(BaseModel):
    name: str
    config: dict


@router.get("/types")
async def list_data_source_types() -> List[DataSourceTypeDto]:
    return [DataSourceTypeDto.from_data_source_class(name=name, data_source_class=data_source_class)
            for name, data_source_class in DataSourceContext.get_data_source_classes().items()]


@router.get("/connected")
async def list_connected_data_sources() -> List[ConnectedDataSourceDto]:
    with Session() as session:
        data_sources = session.query(DataSource).all()
        return [ConnectedDataSourceDto(id=data_source.id, name=data_source.type.name)
                for data_source in data_sources]


@router.delete("/{data_source_id}")
async def delete_data_source(request: Request, data_source_id: int):
    deleted_name = DataSourceContext.delete_data_source(data_source_id=data_source_id)
    BackgroundIndexer.reset_indexed_count()
    Posthog.removed_data_source(uuid=request.headers.get('uuid'), name=deleted_name)
    return {"success": "Data source deleted successfully"}


@router.post("/{data_source_name}/list-locations")
async def list_locations(request: Request, data_source_name: str, config: dict) -> List[Location]:
    data_source = DataSourceContext.get_data_source_class(data_source_name=data_source_name)
    locations = data_source.list_locations(config=config)
    Posthog.listed_locations(uuid=request.headers.get('uuid'), name=data_source_name)
    return locations


@router.post("")
async def connect_data_source(request: Request, dto: AddDataSourceDto, background_tasks: BackgroundTasks) -> int:
    logger.info(f"Adding data source {dto.name} with config {json.dumps(dto.config)}")
    data_source = await DataSourceContext.create_data_source(name=dto.name, config=dto.config)
    Posthog.added_data_source(uuid=request.headers.get('uuid'), name=dto.name)
    # in main.py we have a background task that runs every 5 minutes and indexes the data source
    # but here we want to index the data source immediately
    background_tasks.add_task(data_source.index)

    return data_source.get_id()
