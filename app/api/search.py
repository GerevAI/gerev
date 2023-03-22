from fastapi import APIRouter

from search_logic import search_documents
from telemetry import Posthog

router = APIRouter(
    prefix='/search',
)


@router.get("")
async def search(query: str, top_k: int = 5):
    Posthog.increase_search_count()
    return search_documents(query, top_k)
