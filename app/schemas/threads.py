from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class ThreadCreate(BaseModel):
    thread_title: Optional[str] = Field(default="New Chat")


class ThreadUpdate(BaseModel):
    thread_title: str


class ThreadResponse(BaseModel):
    id: uuid.UUID
    thread_title: str
    user_id: str
    created_at: datetime


class ThreadTitleUpdateRequest(BaseModel):
    thread_id: str
    message: str
