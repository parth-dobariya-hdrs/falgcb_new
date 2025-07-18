# ================================
# FILE: app/api/api_v1/endpoints/chat.py
# ================================
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, StreamingResponse
from app.schemas.chat import ChatRequest, ChatResponse, ChatHistory
from app.services.chat_service import chat_service
from app.dependencies.thread import verify_from_request_body,verify_from_path,verify_from_update_title_req_body
from app.core.database import db_manager
from langchain_google_genai import ChatGoogleGenerativeAI
from app.schemas.threads import ThreadCreate, ThreadResponse
from datetime import datetime, timezone
from typing import List
from uuid import uuid4
from app.schemas.threads import ThreadCreate, ThreadResponse,ThreadTitleUpdateRequest
from datetime import datetime
from typing import List
from app.dependencies.thread import current_active_user,ClerkUser
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Add this endpoint for testing mock streaming
@router.post("/message/stream/mock")
async def send_message_streaming_mock(
    request: ChatRequest
    # user: ClerkUser = Depends(current_active_user),
    # _: None = Depends(verify_from_request_body)
):
    """
    Mock streaming endpoint for testing
    """
    try:
        return StreamingResponse(
            chat_service.process_chat_message_streaming_mock(
                message=request.message,
                thread_id=request.thread_id
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
    except Exception as e:
        logger.error(f"Error in mock streaming endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/message/stream")
async def send_message_streaming(
    request: ChatRequest
    # user: ClerkUser = Depends(current_active_user),
    # _: None = Depends(verify_from_request_body)
):
    """
    Send a message to the chatbot and get a streaming response
    """
    try:
        return StreamingResponse(
            chat_service.process_chat_message_streaming(
                message=request.message,
                thread_id=request.thread_id
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
    except Exception as e:
        logger.error(f"Error in streaming send_message endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest,user: ClerkUser = Depends(current_active_user),_: None = Depends(verify_from_request_body)):
    """
    Send a message to the chatbot and get a response
    """
    try:
        response = await chat_service.process_chat_message(
            message=request.message,
            thread_id=request.thread_id
        )
        return response
    except Exception as e:
        logger.error(f"Error in send_message endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{thread_id}", response_model=ChatHistory)
async def get_chat_history(thread_id: str,user: ClerkUser = Depends(current_active_user), _: None = Depends(verify_from_path)):
    """
    Get chat history for a specific thread
    """
    try:
        history = await chat_service.get_chat_history(thread_id)
        return history
    except Exception as e:
        logger.error(f"Error in get_chat_history endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/history/{thread_id}")
async def clear_chat_history(thread_id: str,user: ClerkUser = Depends(current_active_user),_: None = Depends(verify_from_path)):
    """
    Clear chat history for a specific thread
    """
    try:
        delete= await chat_service.delete_chat_history(thread_id)
        return {"message": f"{delete.response}"}
    except Exception as e:
        logger.error(f"Error in clear_chat_history endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/thread", response_model=ThreadResponse)
async def create_thread(
    thread: ThreadCreate,
    current_user: ClerkUser = Depends(current_active_user)
):
    thread_id = str(uuid4())
    user_id_str = str(current_user.id)
    now = datetime.now(timezone.utc)
    query = """
        INSERT INTO threads (id, user_id, thread_title, created_at)
        VALUES (%s, %s, %s, %s)
        RETURNING id, user_id, thread_title, created_at
    """
    async with db_manager.get_connection() as conn:
        async with conn.cursor() as cur:
            logger.info(f"Creating thread with id: {thread_id}, user_id: {user_id_str}, thread_title: {thread.thread_title}")
            await cur.execute(query, (thread_id, user_id_str, thread.thread_title, now))
            result = await cur.fetchone()

    if result:
        logger.info(f"Thread created successfully with id: {result['id']}, user_id: {result['user_id']}")
        return ThreadResponse(
            id=result['id'],  # type: ignore
            user_id=result['user_id'],  # type: ignore
            thread_title=result['thread_title'],  # type: ignore
            created_at=result['created_at']  # type: ignore
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to create thread")


@router.get("/search", response_model=List[ThreadResponse])
async def search_chat(
    query: str,
    current_user: ClerkUser = Depends(current_active_user)
):
    search_query = f"%{query}%"
    sql = """
        SELECT id, user_id, thread_title, created_at
        FROM threads
        WHERE user_id = %s AND thread_title ILIKE %s
        ORDER BY created_at DESC
    """
    async with db_manager.get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (current_user.id, search_query))
            rows = await cur.fetchall()

    return [
        ThreadResponse(
            id=row['id'],  # type: ignore
            user_id=row['user_id'],  # type: ignore
            thread_title=row['thread_title'],  # type: ignore
            created_at=row['created_at']  # type: ignore
        ) for row in rows
    ]

@router.get("/titles", response_model=List[ThreadResponse])
async def get_chat_titles(
    page: int = 1,
    limit: int = 20,
    current_user: ClerkUser = Depends(current_active_user)
):
    offset = (page - 1) * limit
    query = """
        SELECT id, user_id, thread_title, created_at
        FROM threads
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """
    async with db_manager.get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, (current_user.id, limit, offset))
            rows = await cur.fetchall()

    return [
        ThreadResponse(
            id=row['id'],  # type: ignore
            user_id=row['user_id'],  # type: ignore
            thread_title=row['thread_title'],  # type: ignore
            created_at=row['created_at']  # type: ignore
        ) for row in rows
    ]



@router.post("/update_thread_title", summary="Generate and update thread title using Gemma 3 27B")
async def update_thread_title(
    request: ThreadTitleUpdateRequest,
    user: ClerkUser = Depends(current_active_user),
    _: None = Depends(verify_from_update_title_req_body)
):
    # Initialize LLM
    llm = ChatGoogleGenerativeAI(model="gemma-3-27b-it")

    # Compose a prompt for title generation
    prompt = (
        "Create a single, concise title under 50 characters based ONLY on the first user message below. "
        "Keep it very short, clear, and descriptive. Do not add extra words or variations. "
        "Strictly output only the title text without quotes or extra explanation.\n\n"
        f"User message: {request.message}\n\n"
        "Title:"
    )


    try:
        # Generate title
        response = llm.invoke(prompt)
        if hasattr(response, 'content'):
            title = response.content.strip() if isinstance(response.content, str) else str(response.content).strip()
        else:
            title = str(response).strip()
        logger.info(f"Generated LLM title: {title}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")

    if not title:
        raise HTTPException(status_code=400, detail="Failed to generate title.")

    # Directly update thread title as dependency verifies ownership
    query = """
        UPDATE threads
        SET thread_title = %s
        WHERE id = %s
        RETURNING id
    """
    async with db_manager.get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, (title, request.thread_id))
            result = await cur.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Thread not found or update failed.")

    return {"thread_id": request.thread_id, "new_title": title}

@router.delete(
    "/delete/{thread_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a thread (must be owner and clean up history)",
)
async def delete_thread(
    thread_id: str,
    user: ClerkUser = Depends(current_active_user),
    _ok: None = Depends(verify_from_path),
):
    """
    Delete a thread and its associated chat history.
    Ownership is verified before deletion.
    """
    try:
        # Step 1: Clear chat history (messages, checkpoints, etc.)
        delete_result = await chat_service.delete_chat_history(thread_id)
        logger.info(f"Chat history cleared: {delete_result.response}")

        # Step 2: Delete the thread with transaction
        async with db_manager.get_connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM public.threads WHERE id = %s",
                    (thread_id,),
                )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except Exception as e:
        logger.error(f"Error deleting thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error while deleting thread")
