from fastapi import APIRouter

from search_logic import search_documents

router = APIRouter(
    prefix='/search',
)


@router.get("")
async def search(query: str, top_k: int = 5):
    return search_documents(query, top_k)
