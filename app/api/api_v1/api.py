from fastapi import APIRouter
from app.api.api_v1.endpoints import chat, health

api_router = APIRouter()

api_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["chat"]
)

api_router.include_router(
    health.router,
    prefix="/system",
    tags=["system"]
)
