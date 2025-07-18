# ================================
# FILE: app/services/chat_service.py
# ================================
import json
from typing import AsyncGenerator
from typing import Dict, Any, List
from datetime import datetime
from app.services.langgraph_agent import langgraph_agent
from app.schemas.chat import ChatResponse, ChatHistory, ChatMessage, MessageRole, ChatDelete
import logging
import uuid
import asyncio,re
logger = logging.getLogger(__name__)


class ChatService:
    async def process_chat_message_streaming(
            self,
            message: str,
            thread_id: str
    ) -> AsyncGenerator[str, None]:
        """
        Process a chat message and yield streaming JSON responses
        """
        try:
            message_id = str(uuid.uuid4())
            timestamp = datetime.utcnow()
            
            # Send initial response
            initial_response = {
                "type": "stream_start",
                "thread_id": thread_id,
                "message_id": message_id,
                "timestamp": timestamp.isoformat()
            }
            yield f"data: {json.dumps(initial_response)}\n\n"

            response_content = ""
            tool_calls = []
            accumulated_content = ""

            # Process the message through LangGraph agent
            async for chunk in langgraph_agent.process_message(message, thread_id):
                if "error" in chunk:
                    error_response = {
                        "type": "error",
                        "message": chunk["message"],
                        "thread_id": thread_id,
                        "message_id": message_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    yield f"data: {json.dumps(error_response)}\n\n"
                    return

                # Extract response information
                response_info = langgraph_agent.extract_response_info(chunk)

                # Handle tool calls
                if response_info["is_tool_call"]:
                    tool_calls.extend(response_info["tool_calls"])
                    tool_response = {
                        "type": "tool_calls",
                        "tool_calls": response_info["tool_calls"],
                        "thread_id": thread_id,
                        "message_id": message_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    yield f"data: {json.dumps(tool_response)}\n\n"

                # Handle content - check if we got new content
                if response_info.get("content") and response_info["content"] != accumulated_content:
                    new_content = response_info["content"]
                    
                    # If LangGraph isn't providing incremental chunks, 
                    # we'll artificially chunk the response for streaming effect
                    if len(new_content) > len(accumulated_content):
                        # Get the new part
                        new_part = new_content[len(accumulated_content):]
                        
                        # Artificial chunking - split into words for streaming effect
                        words = new_part.split()
                        current_chunk = ""
                        
                        for word in words:
                            current_chunk += word + " "
                            
                            # Send chunk every few words or at sentence boundaries
                            if (len(current_chunk.split()) >= 3 or 
                                word.endswith('.') or 
                                word.endswith('!') or 
                                word.endswith('?')):
                                
                                content_response = {
                                    "type": "content_chunk",
                                    "content": current_chunk.strip(),
                                    "thread_id": thread_id,
                                    "message_id": message_id,
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                                yield f"data: {json.dumps(content_response)}\n\n"
                                
                                # Small delay to simulate streaming
                                await asyncio.sleep(0.1)
                                current_chunk = ""
                        
                        # Send any remaining content
                        if current_chunk.strip():
                            content_response = {
                                "type": "content_chunk",
                                "content": current_chunk.strip(),
                                "thread_id": thread_id,
                                "message_id": message_id,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            yield f"data: {json.dumps(content_response)}\n\n"
                        
                        accumulated_content = new_content
                    
                    response_content = new_content

                # Check for final response
                if response_info["is_final_response"]:
                    final_response = {
                        "type": "final_response",
                        "response": response_content,
                        "thread_id": thread_id,
                        "message_id": message_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "tool_calls": tool_calls if tool_calls else None
                    }
                    yield f"data: {json.dumps(final_response)}\n\n"
                    break

            # Send stream end signal
            end_response = {
                "type": "stream_end",
                "thread_id": thread_id,
                "message_id": message_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(end_response)}\n\n"

        except Exception as e:
            logger.error(f"Error in streaming chat service: {e}")
            error_response = {
                "type": "error",
                "message": f"I apologize, but I encountered an error: {str(e)}",
                "thread_id": thread_id,
                "message_id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(error_response)}\n\n"

    async def process_chat_message(
            self,
            message: str,
            thread_id: str
    ) -> ChatResponse:
        """
        Process a chat message and return the response
        """
        try:
            response_content = ""
            tool_calls = []

            # Process the message through LangGraph agent
            async for chunk in langgraph_agent.process_message(message, thread_id):
                if "error" in chunk:
                    raise Exception(chunk["message"])

                # Extract response information
                response_info = langgraph_agent.extract_response_info(chunk)

                if response_info["is_tool_call"]:
                    tool_calls.extend(response_info["tool_calls"])
                    logger.info(f"Tool calls made: {response_info['tool_calls']}")

                if response_info["is_final_response"]:
                    response_content = response_info["content"]

            return ChatResponse(
                response=response_content,
                thread_id=thread_id,
                message_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                tool_calls=tool_calls if tool_calls else None
            )

        except Exception as e:
            logger.error(f"Error in chat service: {e}")
            return ChatResponse(
                response=f"I apologize, but I encountered an error: {str(e)}",
                thread_id=thread_id,
                message_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                tool_calls=None
            )

    async def get_chat_history(self, thread_id: str) -> ChatHistory:
        """
        Get chat history for a specific thread
        """
        try:
            history_data = await langgraph_agent.get_chat_history(thread_id)

            messages = []
            for msg_data in history_data:
                messages.append(ChatMessage(
                    role=MessageRole(msg_data["role"]),
                    content=msg_data["content"],
                    timestamp=datetime.fromtimestamp(msg_data["timestamp"]) if msg_data["timestamp"] else None,
                    message_id=msg_data["message_id"]
                ))

            return ChatHistory(
                thread_id=thread_id,
                messages=messages,
                total_messages=len(messages)
            )

        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return ChatHistory(
                thread_id=thread_id,
                messages=[],
                total_messages=0
            )

    async def delete_chat_history(self, thread_id: str) -> ChatDelete:
        """
        Deletes the entire chat history for a specific thread.

        Args:
            thread_id: The identifier of the thread to be deleted.

        Returns:
            A dictionary indicating the status of the deletion operation.
        """
        try:
            # Call the underlying method in your langgraph_agent to perform the deletion
            result = await langgraph_agent.delete_chat_history(thread_id)

            # If the agent returned an error, we raise an exception to be caught below
            if result.get("status") == "error":
                raise Exception(result.get("message", "Unknown error during deletion."))

            # Log and return the result from the agent
            logger.info(f"Successfully deleted history for thread_id: {thread_id}")
            return ChatDelete(
                thread_id=thread_id,
                messages=[],
                response=result
            )

        except Exception as e:
            logger.error(f"Error deleting chat history for thread {thread_id}: {e}")
            return ChatDelete(
                thread_id=thread_id,
                messages=[],
                response={
                    "status": "error",
                    "message": str(e)
                }
            )


# Global chat service instance
chat_service = ChatService()
