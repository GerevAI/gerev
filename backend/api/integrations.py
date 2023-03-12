from fastapi import APIRouter

router = APIRouter(
    prefix='/integrations',
)


@router.get("/list")
async def list_integrations():
    return list_integrations()


@router.post("/add")
async def add_integration(integration: any):
    return add_integration(integration)