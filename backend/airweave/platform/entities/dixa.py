"""Dixa entity schemas.

This module defines the entity schemas for Dixa, including:
    - Conversation entities
    - Message entities
    - Note entities
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from airweave.platform.entities._base import ChunkEntity


class DixaConversationEntity(ChunkEntity):
    """Schema for Dixa conversation entity."""

    name: Optional[str] = Field(None, description="Title or subject of the conversation")
    created_at: datetime = Field(..., description="When the conversation was created")
    updated_at: Optional[datetime] = Field(
        None, description="When the conversation was last updated"
    )
    status: str = Field(..., description="Status of the conversation")
    content: str = Field(..., description="Content/summary of the conversation")


class DixaMessageEntity(ChunkEntity):
    """Schema for Dixa message entity."""

    conversation_id: str = Field(..., description="ID of the parent conversation")
    created_at: datetime = Field(..., description="When the message was created")
    content: str = Field(..., description="Content of the message")
    author_type: str = Field(..., description="Type of the message author (agent/customer)")
    author_name: Optional[str] = Field(None, description="Name of the message author")


class DixaNoteEntity(ChunkEntity):
    """Schema for Dixa internal note entity."""

    conversation_id: str = Field(..., description="ID of the parent conversation")
    created_at: datetime = Field(..., description="When the note was created")
    content: str = Field(..., description="Content of the internal note")
    author_name: Optional[str] = Field(None, description="Name of the note author")
