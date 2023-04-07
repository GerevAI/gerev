from fastapi import APIRouter
from starlette.requests import Request

from search_logic import search_documents
from telemetry import Posthog

router = APIRouter(
    prefix='/search',
)


@router.get("")
async def search(request: Request, query: str, top_k: int = 10):
    uuid_header = request.headers.get('uuid')
    Posthog.increase_search_count(uuid=uuid_header)
    return search_documents(query, top_k)
