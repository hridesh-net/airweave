"""Chat service for handling AI interactions."""

import logging
from typing import AsyncGenerator, Optional
from uuid import UUID

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionChunk
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.core.config import settings
from app.core.search_service import search_service
from app.core.search_type import SearchType
from app.models.chat import ChatMessage, ChatRole

logger = logging.getLogger(__name__)


class ChatService:
    """Service for handling chat interactions with AI."""

    DEFAULT_MODEL = "gpt-4o"
    DEFAULT_MODEL_SETTINGS = {
        "temperature": 0.7,
        "max_tokens": 1000,
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0,
    }

    CONTEXT_PROMPT = """You are an AI assistant with access to a knowledge base.
    Use the following relevant context to help answer the user's question.
    Always format your responses in proper markdown, including:
    - Using proper headers (# ## ###)
    - Formatting code blocks with ```language
    - Using tables with | header | header |
    - Using bullet points and numbered lists
    - Using **bold** and *italic* where appropriate

    Here's the context:
    {context}

    Remember to:
    1. Be helpful, clear, and accurate
    2. Maintain a professional tone
    3. Format ALL responses in proper markdown
    4. Use tables when presenting structured data
    5. Use code blocks with proper language tags"""

    def __init__(self):
        """Initialize the chat service with OpenAI client."""
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY is not set in environment variables")
            self.client = None
        else:
            self.client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
            )

    async def generate_streaming_response(
        self,
        db: AsyncSession,
        chat_id: UUID,
        user: schemas.User,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Generate a streaming AI response.

        Args:
            db (AsyncSession): Database session
            chat_id (UUID): Chat ID
            user (schemas.User): Current user

        Yields:
            AsyncGenerator[ChatCompletionChunk]: Stream of response entities
        """
        try:
            chat = await crud.chat.get_with_messages(db=db, id=chat_id, current_user=user)
            if not chat:
                logger.error(f"Chat {chat_id} not found")
                return

            # Get relevant context from last user message
            last_user_message = next(
                (msg for msg in reversed(chat.messages) if msg.role == ChatRole.USER), None
            )
            context = ""
            if last_user_message:
                context = await self._get_relevant_context(
                    db=db,
                    chat=chat,
                    query=last_user_message.content,
                    user=user,
                )

            # Prepare messages with context
            messages = self._prepare_messages_with_context(chat.messages, context)

            # Merge settings
            model = chat.model_name or self.DEFAULT_MODEL
            model_settings = {
                **self.DEFAULT_MODEL_SETTINGS,
                **chat.model_settings,
                "stream": True,  # Enable streaming
            }

            # Create streaming response
            stream = await self.client.chat.completions.create(
                model=model, messages=messages, **model_settings
            )

            full_content = ""
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_content += chunk.choices[0].delta.content
                yield chunk

            # Save the complete message after streaming
            if full_content:
                message_create = schemas.ChatMessageCreate(
                    content=full_content,
                    role=ChatRole.ASSISTANT,
                )
                await crud.chat.add_message(
                    db=db, chat_id=chat_id, obj_in=message_create, current_user=user
                )

        except Exception as e:
            logger.error(f"Error generating streaming response: {str(e)}")
            # Create error message
            error_message = schemas.ChatMessageCreate(
                content=(
                    "Sorry, I encountered an error while generating a response. Please try again."
                ),
                role=ChatRole.ASSISTANT,
            )
            await crud.chat.add_message(
                db=db, chat_id=chat_id, obj_in=error_message, current_user=user
            )
            raise

    async def generate_and_save_response(
        self,
        db: AsyncSession,
        chat_id: UUID,
        user: schemas.User,
    ) -> Optional[ChatMessage]:
        """Generate a non-streaming AI response and save it."""
        try:
            chat = await crud.chat.get_with_messages(db=db, id=chat_id, current_user=user)
            if not chat:
                logger.error(f"Chat {chat_id} not found")
                return None

            messages = self._prepare_messages(chat.messages)
            model = chat.model_name or self.DEFAULT_MODEL
            model_settings = {
                **self.DEFAULT_MODEL_SETTINGS,
                **chat.model_settings,
            }

            response = await self.client.chat.completions.create(
                model=model, messages=messages, **model_settings
            )

            if not response.choices:
                logger.error("No response generated from OpenAI")
                return None

            message_create = schemas.ChatMessageCreate(
                content=response.choices[0].message.content,
                role=ChatRole.ASSISTANT,
            )

            return await crud.chat.add_message(
                db=db, chat_id=chat_id, obj_in=message_create, current_user=user
            )

        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            error_message = schemas.ChatMessageCreate(
                content=(
                    "Sorry, I encountered an error while generating a response. Please try again."
                ),
                role=ChatRole.ASSISTANT,
            )
            return await crud.chat.add_message(
                db=db, chat_id=chat_id, obj_in=error_message, current_user=user
            )

    def _prepare_messages(self, messages: list[ChatMessage]) -> list[dict]:
        """Prepare messages for OpenAI API format."""
        formatted_messages = []
        has_system_message = any(msg.role == ChatRole.SYSTEM for msg in messages)

        if not has_system_message:
            formatted_messages.append(
                {
                    "role": "system",
                    "content": (
                        "You are a helpful AI assistant. Provide clear, accurate, "
                        "and concise responses while being friendly and professional."
                    ),
                }
            )

        formatted_messages.extend(
            [{"role": message.role, "content": message.content} for message in messages]
        )

        return formatted_messages

    async def _get_relevant_context(
        self,
        db: AsyncSession,
        chat: schemas.Chat,
        query: str,
        user: schemas.User,
    ) -> str:
        """Get relevant context for the query from vector search.

        Args:
            db: Database session
            chat: Chat object
            query: Query string
            user: Current user

        Returns:
            str: Relevant context as a string
        """
        if not chat.sync_id:
            return ""

        try:
            # Get search type preference from chat settings
            search_type = SearchType.VECTOR  # Default to vector search
            if chat.settings and "search_type" in chat.settings:
                try:
                    search_type = SearchType(chat.settings["search_type"])
                except (ValueError, KeyError):
                    # Invalid search type, fall back to vector
                    pass

            # Perform search based on the search type
            results = await search_service.search(
                db=db,
                query=query,
                sync_id=chat.sync_id,
                current_user=user,
                search_type=search_type,
                limit=5,  # Limit to top 5 results
            )

            # Format results based on search type
            if search_type == SearchType.HYBRID:
                # For hybrid search, combine vector and graph results
                vector_results = results.get("vector", [])
                graph_results = results.get("graph", [])

                # Format vector results
                vector_context = ""
                if vector_results:
                    vector_context = "Vector search results:\n\n"
                    for i, result in enumerate(vector_results[:3], 1):  # Limit to top 3
                        vector_context += f"{i}. {self._format_search_result(result)}\n\n"

                # Format graph results
                graph_context = ""
                if graph_results:
                    graph_context = "Graph search results (showing relationships):\n\n"
                    for i, result in enumerate(graph_results[:3], 1):  # Limit to top 3
                        graph_context += f"{i}. {self._format_search_result(result)}\n\n"

                # Combine contexts
                return f"{vector_context}\n{graph_context}".strip()
            else:
                # For single search type (vector or graph)
                if not results:
                    return ""

                context = ""
                for i, result in enumerate(results[:5], 1):
                    context += f"{i}. {self._format_search_result(result)}\n\n"

                return context

        except Exception as e:
            logger.error(f"Error getting context: {str(e)}")
            return ""

    def _format_search_result(self, result: dict) -> str:
        """Format a search result for inclusion in context.

        Args:
            result: Search result dictionary

        Returns:
            str: Formatted search result
        """
        # Extract common fields
        content = result.get("content", "")
        name = result.get("name", "")
        entity_type = result.get("entity_type", "")

        # Format based on available fields
        if name and content:
            return f"{name} ({entity_type}):\n{content}"
        elif name:
            return f"{name} ({entity_type})"
        elif content:
            return content
        else:
            # Fallback to returning the whole result as a string
            return str(result)

    def _prepare_messages_with_context(
        self,
        messages: list[ChatMessage],
        context: str = "",
    ) -> list[dict]:
        """Prepare messages for OpenAI API format with optional context."""
        formatted_messages = []
        has_system_message = any(msg.role == ChatRole.SYSTEM for msg in messages)

        # Add system message with context if available
        if not has_system_message:
            system_content = (
                self.CONTEXT_PROMPT.format(context=context)
                if context
                else (
                    "You are a helpful AI assistant. "
                    "Always format your responses in proper markdown, "
                    "including tables, code blocks with language tags, and proper headers. "
                    "Provide clear, accurate, and concise responses while being friendly"
                    " and professional."
                )
            )
            formatted_messages.append(
                {
                    "role": "system",
                    "content": system_content,
                }
            )

        # Add chat history
        formatted_messages.extend(
            [{"role": message.role, "content": message.content} for message in messages]
        )

        return formatted_messages


# Create a singleton instance
chat_service = ChatService()
