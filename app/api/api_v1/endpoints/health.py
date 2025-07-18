# ================================
# FILE: app/api/api_v1/endpoints/health.py
# ================================
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_users.db import SQLAlchemyUserDatabase
from typing import Optional
import os

from app.core.database import User, get_user_db
from fastapi import APIRouter
from app.schemas.chat import HealthCheck
from app.core.config import settings
from datetime import datetime

router = APIRouter()


@router.get("/health", response_model=HealthCheck)
async def health_check():
    """
    Health check endpoint
    """
    return HealthCheck(
        status="healthy",
        timestamp=datetime.utcnow(),
        version=settings.VERSION
    )
