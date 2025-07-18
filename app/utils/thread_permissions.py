# app/utils/thread_permissions.py

from fastapi import HTTPException, status
from app.core.database import db_manager


async def verify_thread_ownership(thread_id: str, user_id: str) -> None:
    async with db_manager.get_connection() as conn:
        result = await conn.execute(
            "SELECT 1 FROM threads WHERE id = %s AND user_id = %s LIMIT 1",
            (thread_id, user_id)
        )
        row = await result.fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this thread."
            )
