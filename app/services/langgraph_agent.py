# ================================
# FILE: app/services/langgraph_agent.py
# ================================

import os
import uuid
from typing import AsyncGenerator, Dict, Any, List
from pydantic import SecretStr
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage, AIMessage
from app.core.config import settings
from app.core.database import db_manager
import logging

logger = logging.getLogger(__name__)


class LangGraphAgent:
    def __init__(self):
        self.llm = None
        self.tavily = None
        self.agent = None
        self._initialize_components()

    def _initialize_components(self):
        """Initialize LLM, tools, and agent"""
        try:
            # Initialize LLM
            self.llm = ChatGroq(
                api_key=SecretStr(settings.GROQ_API_KEY),
                model="qwen/qwen3-32b",
                temperature=0.1,
            )

            # Initialize Tavily search tool
            self.tavily = TavilySearchResults(
                api_key=SecretStr(settings.TAVILY_API_KEY),
                max_results=3
            )

            logger.info("LangGraph agent components initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize LangGraph agent: {e}")
            raise

    def _create_agent(self, memory: AsyncPostgresSaver):
        """Create the LangGraph agent with checkpointer"""
        if self.llm is None:
            raise ValueError("LLM is not initialized")
        if self.tavily is None:
            raise ValueError("Tavily search tool is not initialized")
        return create_react_agent(
            model=self.llm,
            tools=[self.tavily],
            checkpointer=memory
        )

    async def process_message(
            self,
            message: str,
            thread_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a user message and yield streaming responses
        """
        try:
            memory = db_manager.get_memory_checkpointer()

            # Create agent with current memory instance
            agent = self._create_agent(memory)

            # Stream the agent's response
            async for chunk in agent.astream(
                    {"messages": [HumanMessage(content=message)]},
                    {"configurable": {"thread_id": thread_id}}
            ):
                yield chunk

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            yield {
                "error": True,
                "message": f"Failed to process message: {str(e)}"
            }

    async def get_chat_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """
        Get chat history for a specific thread - returns only human messages and AI responses
        (excludes tool calls and system messages for frontend display)
        """
        try:
            memory = db_manager.get_memory_checkpointer()

            # Get all checkpoints for this thread
            checkpoints = []
            try:
                async for checkpoint in memory.alist(
                        {"configurable": {"thread_id": thread_id}}):  # type: ignore[arg-type]
                    checkpoints.append(checkpoint)
            except Exception as list_error:
                logger.warning(f"Error listing checkpoints for thread {thread_id}: {list_error}")
                return []

            if not checkpoints:
                logger.info(f"No checkpoints found for thread {thread_id} - returning empty history")
                return []

            processed_messages = []
            seen_message_ids = set()  # To avoid duplicates

            for checkpoint in checkpoints:
                # Handle CheckpointTuple structure
                try:
                    # CheckpointTuple has attributes: checkpoint, metadata, config, parent_config
                    if hasattr(checkpoint, 'checkpoint'):
                        checkpoint_data = checkpoint.checkpoint
                    else:
                        checkpoint_data = checkpoint

                    # Try different possible paths for messages
                    messages = None
                    if hasattr(checkpoint_data, 'channel_values') and checkpoint_data.channel_values:
                        messages = checkpoint_data.channel_values.get("messages", [])
                    elif isinstance(checkpoint_data, dict):
                        if "channel_values" in checkpoint_data:
                            messages = checkpoint_data["channel_values"].get("messages", [])
                        elif "messages" in checkpoint_data:
                            messages = checkpoint_data["messages"]
                        elif "values" in checkpoint_data:
                            messages = checkpoint_data["values"].get("messages", [])

                    if not messages:
                        continue
                except Exception as checkpoint_error:
                    logger.warning(f"Error processing checkpoint: {checkpoint_error}")
                    continue

                for message in messages:
                    # Skip tool calls and system messages - only process HumanMessage and AIMessage
                    if not isinstance(message, (HumanMessage, AIMessage)):
                        continue

                    # Additional check to filter out AI messages that are tool calls
                    if isinstance(message, AIMessage):
                        # Check if this is a tool call message by looking for tool_calls in content or additional_kwargs
                        if hasattr(message, 'tool_calls') and message.tool_calls:
                            continue
                        if hasattr(message, 'additional_kwargs') and message.additional_kwargs:
                            if message.additional_kwargs.get('tool_calls') or message.additional_kwargs.get(
                                    'function_call'):
                                continue
                        # Skip if content is empty (might be a tool call with no text response)
                        if not message.content or (isinstance(message.content, str) and not message.content.strip()):
                            continue

                    # Generate a unique identifier for deduplication
                    message_content = getattr(message, 'content', '') if hasattr(message, 'content') else str(message)
                    message_type = type(message).__name__
                    message_key = f"{message_type}:{hash(str(message_content))}"

                    if message_key in seen_message_ids:
                        continue
                    seen_message_ids.add(message_key)

                    # Get the timestamp from various possible sources
                    timestamp = None
                    if hasattr(message, "additional_kwargs") and message.additional_kwargs:
                        timestamp = message.additional_kwargs.get("timestamp")

                    # Fallback to checkpoint timestamp
                    if not timestamp:
                        if hasattr(checkpoint, 'metadata') and checkpoint.metadata:
                            timestamp = checkpoint.metadata.get('ts') or checkpoint.metadata.get('created_at')
                        elif isinstance(checkpoint_data, dict):
                            timestamp = checkpoint_data.get('ts') or checkpoint_data.get('created_at')

                    # Get message ID
                    message_id = None
                    if hasattr(message, "id") and message.id:
                        message_id = message.id
                    else:
                        message_id = str(uuid.uuid4())

                    if isinstance(message, HumanMessage):
                        processed_messages.append({
                            "role": "user",
                            "content": message.content,
                            "message_id": message_id,
                            "timestamp": timestamp
                        })
                    elif isinstance(message, AIMessage):
                        processed_messages.append({
                            "role": "assistant",
                            "content": message.content,
                            "message_id": message_id,
                            "timestamp": timestamp
                        })

            # Sort messages by timestamp to maintain chronological order
            # Handle None timestamps by putting them at the beginning
            processed_messages.sort(key=lambda x: x["timestamp"] if x["timestamp"] is not None else 0)

            return processed_messages

        except Exception as e:
            logger.error(f"Error getting chat history for thread {thread_id}: {e}")
            return []

    async def delete_chat_history(self, thread_id: str) -> Dict[str, Any]:
        """
        Deletes all chat history for a specific thread_id.

        Args:
            thread_id: The identifier of the thread to delete.

        Returns:
            A dictionary with the status of the operation.
        """
        try:
            # Get the checkpointer instance
            memory = db_manager.get_memory_checkpointer()
            config = {"configurable": {"thread_id": thread_id}}

            # First, get all checkpoints to verify what exists
            checkpoints_before = []
            async for checkpoint in memory.alist(config):  # type: ignore[arg-type]
                checkpoints_before.append(checkpoint)

            if not checkpoints_before:
                logger.info(f"No history found for thread {thread_id}")
                return {
                    "status": "success",
                    "message": f"No history found for thread {thread_id}."
                }

            # Delete the thread's history with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                # Delete the thread's history
                await memory.adelete_thread(thread_id)  # Directly pass thread_id as it's used directly in SQL

                # Force a sync or commit if possible to ensure deletion is visible
                if hasattr(memory, 'pipe') and memory.pipe:
                    await memory.pipe.sync()

                # Verify deletion by checking if any checkpoints remain
                checkpoints_after = []
                async for checkpoint in memory.alist(config):  # type: ignore[arg-type]
                    checkpoints_after.append(checkpoint)

                if not checkpoints_after:
                    # Successfully deleted all checkpoints
                    logger.info(
                        f"Successfully deleted {len(checkpoints_before)} checkpoints for thread_id: {thread_id} on attempt {attempt + 1}")
                    return {
                        "status": "success",
                        "message": f"Deleted {len(checkpoints_before)} messages from thread {thread_id}."
                    }

                # Log remaining checkpoints and retry
                logger.warning(
                    f"Attempt {attempt + 1}: {len(checkpoints_after)} checkpoints remain for thread {thread_id}. Retrying...")

            # If we reach here, all retries failed
            logger.error(
                f"Failed to delete all history for thread {thread_id} after {max_retries} attempts. {len(checkpoints_after)} checkpoints remain.")
            return {
                "status": "error",
                "message": f"Failed to delete all history for thread {thread_id} after {max_retries} attempts. {len(checkpoints_after)} checkpoints remain."
            }

        except Exception as e:
            logger.error(f"Error deleting chat history for thread {thread_id}: {e}")
            return {
                "status": "error",
                "message": f"An error occurred while deleting history: {e}"
            }

    def extract_response_info(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant information from agent chunk
        """
        result = {
            "content": "",
            "tool_calls": [],
            "is_tool_call": False,
            "is_final_response": False
        }

        if "agent" in chunk:
            for message in chunk["agent"]["messages"]:
                # Check for tool calls
                if hasattr(message, 'additional_kwargs') and "tool_calls" in message.additional_kwargs:
                    result["is_tool_call"] = True
                    tool_calls = message.additional_kwargs["tool_calls"]

                    for tool_call in tool_calls:
                        result["tool_calls"].append({
                            "tool_name": tool_call["function"]["name"],
                            "query": eval(tool_call["function"]["arguments"]).get("query", "")
                        })
                else:
                    # Final response
                    result["is_final_response"] = True
                    result["content"] = message.content

        return result


# Global agent instance
langgraph_agent = LangGraphAgent()
