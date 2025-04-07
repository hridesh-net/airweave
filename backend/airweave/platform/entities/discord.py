"""Discord entities."""

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from airweave.platform.entities._base import BaseEntity, ChunkEntity, FileEntity


class DiscordUserEntity(BaseEntity):
    """Schema for Discord user entity."""

    username: str = Field(..., description="Username of the Discord user")
    discriminator: str = Field(..., description="4-digit discriminator of the user")
    avatar: Optional[str] = Field(None, description="User's avatar hash")
    bot: bool = Field(False, description="Whether the user is a bot")
    email: Optional[str] = Field(None, description="User's email if available")


class DiscordChannelEntity(BaseEntity):
    """Schema for Discord channel entity."""

    name: str = Field(..., description="Name of the channel")
    type: int = Field(..., description="Type of channel")
    guild_id: str = Field(..., description="ID of the guild this channel belongs to")
    position: Optional[int] = Field(None, description="Position of the channel")
    topic: Optional[str] = Field(None, description="Channel topic")
    nsfw: bool = Field(False, description="Whether the channel is NSFW")
    parent_id: Optional[str] = Field(None, description="ID of the parent category")


class DiscordMessageEntity(ChunkEntity):
    """Schema for Discord message entity."""

    content: str = Field(..., description="Content of the message")
    author_id: str = Field(..., description="ID of the message author")
    channel_id: str = Field(..., description="ID of the channel the message was sent in")
    guild_id: str = Field(..., description="ID of the guild the message was sent in")
    created_at: datetime = Field(..., description="Timestamp when the message was created")
    edited_at: Optional[datetime] = Field(
        None, description="Timestamp when the message was last edited"
    )
    pinned: bool = Field(False, description="Whether the message is pinned")
    mention_everyone: bool = Field(False, description="Whether the message mentions everyone")
    attachments: List[str] = Field(default_factory=list, description="List of attachment URLs")


class DiscordAttachmentEntity(FileEntity):
    """Schema for Discord file attachments."""

    filename: str = Field(..., description="Name of the file")
    size: int = Field(..., description="Size of the file in bytes")
    url: str = Field(..., description="URL of the file")
    content_type: Optional[str] = Field(None, description="MIME type of the file")
    height: Optional[int] = Field(None, description="Height of the file if it is an image")
    width: Optional[int] = Field(None, description="Width of the file if it is an image")
