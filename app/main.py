# ================================
# FILE: app/main.py
# ================================

import logging
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from app.core.config import settings
from app.core.database import db_manager
from app.api.api_v1.api import api_router
from app.dependencies.thread import current_active_user,ClerkUser
# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up FastAPI LangGraph Chatbot...")
    await db_manager.initialize()
    logger.info("Database initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await db_manager.close()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Set up CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {
        "message": "FastAPI LangGraph Chatbot API",
        "version": settings.VERSION,
        "docs_url": "/docs"
    }


# --- Protected Route Example ---
@app.get("/protected-route")
def protected_route(user: ClerkUser = Depends(current_active_user)):
    return f"Hello, {user.email}. You are accessing a protected route."

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
