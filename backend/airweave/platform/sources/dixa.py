"""Dixa source implementation.

This connector retrieves data from Dixa's API:
    - Conversations
    - Messages
    - Notes
"""

import logging
from datetime import datetime
from typing import AsyncGenerator, Optional

import httpx
import tenacity
from tenacity import retry_if_exception_type, stop_after_attempt, wait_exponential

from airweave.platform.auth.schemas import AuthType
from airweave.platform.decorators import source
from airweave.platform.entities._base import ChunkEntity
from airweave.platform.entities.dixa import (
    DixaConversationEntity,
    DixaMessageEntity,
    DixaNoteEntity,
)
from airweave.platform.sources._base import BaseSource

logger = logging.getLogger(__name__)


@source("Dixa", "dixa", AuthType.api_key)
class DixaSource(BaseSource):
    """Dixa source implementation."""

    BASE_URL = "https://dev.dixa.io/v1"

    @classmethod
    async def create(cls, api_key: str) -> "DixaSource":
        """Create a new source instance with authentication."""
        instance = cls()
        instance.api_key = api_key
        return instance

    @tenacity.retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    async def _get_with_auth(
        self, client: httpx.AsyncClient, url: str, params: Optional[dict] = None
    ) -> dict:
        """Make authenticated API request."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error occurred: {str(e)}")
            msg = e.response.content if hasattr(e, "response") else "No response"
            logger.error(f"Response content: {msg}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred: {str(e)}")
            raise

    async def _generate_conversation_entities(
        self, client: httpx.AsyncClient
    ) -> AsyncGenerator[ChunkEntity, None]:
        """Generate entities from conversations."""
        url = f"{self.BASE_URL}/conversations"
        logger.info(f"Fetching conversations from {url}")

        page = 1
        while True:
            params = {"page": page, "limit": 100}
            try:
                response = await self._get_with_auth(client, url, params)
                conversations = response.get("data", [])

                if not conversations:
                    logger.info(f"No more conversations found after page {page}")
                    break

                logger.info(f"Processing {len(conversations)} conversations from page {page}")

                for conv in conversations:
                    try:
                        # Create conversation entity
                        conversation = DixaConversationEntity(
                            entity_id=str(conv["id"]),  # Ensure ID is string
                            name=conv.get("subject"),
                            created_at=datetime.fromisoformat(
                                conv["created_at"].replace("Z", "+00:00")
                            ),
                            updated_at=datetime.fromisoformat(
                                conv["updated_at"].replace("Z", "+00:00")
                            )
                            if "updated_at" in conv
                            else None,
                            status=conv.get("status", "unknown"),
                            content=conv.get("summary", ""),
                        )
                        yield conversation

                        # Get messages for this conversation
                        async for message in self._generate_message_entities(client, conv["id"]):
                            yield message

                        # Get notes for this conversation
                        async for note in self._generate_note_entities(client, conv["id"]):
                            yield note

                    except Exception as e:
                        logger.error(f"Error processing conversation {conv.get('id')}: {str(e)}")
                        continue

                page += 1
            except Exception as e:
                logger.error(f"Error fetching page {page}: {str(e)}")
                break

    async def _generate_message_entities(
        self, client: httpx.AsyncClient, conversation_id: str
    ) -> AsyncGenerator[ChunkEntity, None]:
        """Generate entities from messages in a conversation."""
        url = f"{self.BASE_URL}/conversations/{conversation_id}/messages"
        logger.info(f"Fetching messages for conversation {conversation_id}")

        try:
            response = await self._get_with_auth(client, url)
            messages = response.get("data", [])
            logger.info(f"Found {len(messages)} messages for conversation {conversation_id}")

            for msg in messages:
                try:
                    yield DixaMessageEntity(
                        entity_id=str(msg["id"]),
                        conversation_id=str(conversation_id),
                        created_at=datetime.fromisoformat(msg["created_at"].replace("Z", "+00:00")),
                        content=msg.get("content", ""),
                        author_type=msg.get("author_type", "unknown"),
                        author_name=msg.get("author_name"),
                    )
                except Exception as e:
                    logger.error(f"Error processing message {msg.get('id')}: {str(e)}")
                    continue
        except Exception as e:
            logger.error(f"Error fetching messages for conversation {conversation_id}: {str(e)}")

    async def _generate_note_entities(
        self, client: httpx.AsyncClient, conversation_id: str
    ) -> AsyncGenerator[ChunkEntity, None]:
        """Generate entities from notes in a conversation."""
        url = f"{self.BASE_URL}/conversations/{conversation_id}/notes"
        logger.info(f"Fetching notes for conversation {conversation_id}")

        try:
            response = await self._get_with_auth(client, url)
            notes = response.get("data", [])
            logger.info(f"Found {len(notes)} notes for conversation {conversation_id}")

            for note in notes:
                try:
                    yield DixaNoteEntity(
                        entity_id=str(note["id"]),
                        conversation_id=str(conversation_id),
                        created_at=datetime.fromisoformat(
                            note["created_at"].replace("Z", "+00:00")
                        ),
                        content=note.get("content", ""),
                        author_name=note.get("author_name"),
                    )
                except Exception as e:
                    logger.error(f"Error processing note {note.get('id')}: {str(e)}")
                    continue
        except Exception as e:
            logger.error(f"Error fetching notes for conversation {conversation_id}: {str(e)}")

    async def generate_entities(self) -> AsyncGenerator[ChunkEntity, None]:
        """Main entry point to generate all entities."""
        logger.info("Starting Dixa entity generation")
        async with httpx.AsyncClient() as client:
            try:
                async for entity in self._generate_conversation_entities(client):
                    yield entity
            except Exception as e:
                logger.error(f"Error in generate_entities: {str(e)}")
                raise
