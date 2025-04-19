"""Discord entity definitions for Airweave."""
from datetime import datetime
from typing import List, Optional

from pydantic import Field

from airweave.platform.entities._base import BaseEntity, ChunkEntity, FileEntity


class DiscordGuildEntity(ChunkEntity):
    """Schema for Discord guild (server) entity."""

    name: str = Field(..., description="Name of the guild")
    description: Optional[str] = Field(None, description="Description of the guild")
    icon_url: Optional[str] = Field(None, description="URL of the guild's icon")
    created_at: datetime = Field(..., description="When the guild was created")


class DiscordChannelEntity(ChunkEntity):
    """Schema for Discord channel entity."""

    name: str = Field(..., description="Name of the channel")
    type: str = Field(..., description="Type of channel (text, voice, etc.)")
    topic: Optional[str] = Field(None, description="Channel topic/description")
    created_at: datetime = Field(..., description="When the channel was created")
    is_nsfw: bool = Field(False, description="Whether the channel is NSFW")
    parent_id: Optional[str] = Field(None, description="ID of the parent category")
    position: int = Field(..., description="Position of the channel in the guild")


class DiscordMessageEntity(ChunkEntity):
    """Schema for Discord message entity."""

    content: str = Field(..., description="Content of the message")
    author_id: str = Field(..., description="ID of the message author")
    channel_id: str = Field(..., description="ID of the channel containing the message")
    created_at: datetime = Field(..., description="When the message was created")
    edited_at: Optional[datetime] = Field(None, description="When the message was last edited")
    pinned: bool = Field(False, description="Whether the message is pinned")
    thread_id: Optional[str] = Field(None, description="ID of the thread if message started a thread")


class DiscordUserEntity(ChunkEntity):
    """Schema for Discord user entity."""

    username: str = Field(..., description="Username of the user")
    discriminator: str = Field(..., description="User's discriminator")
    display_name: Optional[str] = Field(None, description="User's display name")
    avatar_url: Optional[str] = Field(None, description="URL of the user's avatar")
    bot: bool = Field(False, description="Whether the user is a bot")
    created_at: datetime = Field(..., description="When the user account was created")


class DiscordThreadEntity(ChunkEntity):
    """Schema for Discord thread entity."""

    name: str = Field(..., description="Name of the thread")
    parent_id: str = Field(..., description="ID of the parent channel")
    owner_id: str = Field(..., description="ID of the thread creator")
    created_at: datetime = Field(..., description="When the thread was created")
    archived: bool = Field(False, description="Whether the thread is archived")
    locked: bool = Field(False, description="Whether the thread is locked")
    message_count: int = Field(..., description="Number of messages in the thread")


class DiscordAttachmentEntity(FileEntity):
    """Schema for Discord attachment entity."""

    message_id: str = Field(..., description="ID of the message containing the attachment")
    channel_id: str = Field(..., description="ID of the channel containing the attachment")
    description: Optional[str] = Field(None, description="Description of the attachment")
    content_type: Optional[str] = Field(None, description="Content type of the attachment")
    height: Optional[int] = Field(None, description="Height of the attachment if it's an image")
    width: Optional[int] = Field(None, description="Width of the attachment if it's an image") 