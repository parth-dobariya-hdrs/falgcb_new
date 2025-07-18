# ================================
# FILE: app/utils/helpers.py
# ================================

import uuid
from datetime import datetime
from typing import Optional
from datetime import datetime, timezone


def get_current_timestamp() -> datetime:
    """Get current UTC timestamp (timezone-aware)"""
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    """Generate a UUID string"""
    return str(uuid.uuid4())


def format_timestamp(timestamp: datetime) -> str:
    """Format timestamp to ISO string"""
    return timestamp.isoformat()


def validate_thread_id(thread_id: str) -> bool:
    """Validate thread ID format"""
    if not thread_id or len(thread_id) > 100:
        return False
    return True
