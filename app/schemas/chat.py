# FILE: app/schemas/chat.py
# ================================

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: Optional[datetime] = None
    message_id: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    thread_id: str = Field(..., min_length=1, max_length=100)


class ChatResponse(BaseModel):
    response: str
    thread_id: str
    message_id: Optional[str] = None
    timestamp: datetime
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ChatHistory(BaseModel):
    thread_id: str
    messages: List[ChatMessage]
    total_messages: int


class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    version: str


class ChatDelete(BaseModel):
    thread_id: str
    messages: List[ChatMessage]
    response: Dict
