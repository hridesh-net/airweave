"""Discord source implementation for Airweave."""
import logging
from datetime import datetime
from typing import AsyncGenerator, Dict, List, Optional
import asyncio

import httpx

from airweave.platform.decorators import source
from airweave.platform.auth.schemas import AuthType
from airweave.platform.entities._base import ChunkEntity, FileEntity
from airweave.platform.entities.discord import (
    DiscordAttachmentEntity,
    DiscordChannelEntity,
    DiscordGuildEntity,
    DiscordMessageEntity,
    DiscordThreadEntity,
    DiscordUserEntity,
)
from airweave.platform.sources._base import BaseSource

logger = logging.getLogger(__name__)


@source("Discord", "discord", AuthType.oauth2)
class DiscordSource(BaseSource):
    """Discord source implementation."""

    BASE_URL = "https://discord.com/api/v10"
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds

    @classmethod
    async def create(cls, access_token: str) -> "DiscordSource":
        """Create a new source instance with authentication."""
        instance = cls()
        instance.access_token = access_token
        return instance

    async def _get_with_auth(
        self, client: httpx.AsyncClient, url: str, params: Optional[dict] = None
    ) -> dict:
        """Make authenticated API request with retries."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "Airweave Discord Integration (https://github.com/airweave/airweave)",
        }

        for attempt in range(self.MAX_RETRIES):
            try:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                if attempt == self.MAX_RETRIES - 1:  # Last attempt
                    logger.error(f"Error calling Discord API: {str(e)}")
                    raise
                await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))  # Exponential backoff

    async def _generate_guild_entities(
        self, client: httpx.AsyncClient
    ) -> AsyncGenerator[DiscordGuildEntity, None]:
        """Generate guild entities."""
        url = f"{self.BASE_URL}/users/@me/guilds"
        response = await self._get_with_auth(client, url)

        for guild in response:
            created_at = datetime.fromtimestamp(
                ((int(guild["id"]) >> 22) + 1420070400000) / 1000
            )
            yield DiscordGuildEntity(
                entity_id=guild["id"],
                name=guild["name"],
                description=guild.get("description"),
                icon_url=f"https://cdn.discordapp.com/icons/{guild['id']}/{guild['icon']}.png"
                if guild.get("icon")
                else None,
                created_at=created_at,
                content=guild.get("description", ""),
            )

    async def _generate_channel_entities(
        self, client: httpx.AsyncClient, guild_id: str, guild_breadcrumb: dict
    ) -> AsyncGenerator[DiscordChannelEntity, None]:
        """Generate channel entities for a guild."""
        url = f"{self.BASE_URL}/guilds/{guild_id}/channels"
        response = await self._get_with_auth(client, url)

        for channel in response:
            if channel["type"] not in [0, 2, 5, 10, 11, 12]:  # Text, voice, announcement, thread
                continue

            created_at = datetime.fromtimestamp(
                ((int(channel["id"]) >> 22) + 1420070400000) / 1000
            )
            yield DiscordChannelEntity(
                entity_id=channel["id"],
                name=channel["name"],
                type=str(channel["type"]),
                topic=channel.get("topic"),
                created_at=created_at,
                is_nsfw=channel.get("nsfw", False),
                parent_id=channel.get("parent_id"),
                position=channel["position"],
                content=channel.get("topic", ""),
                breadcrumbs=[guild_breadcrumb],
            )

    async def _generate_message_entities(
        self,
        client: httpx.AsyncClient,
        channel_id: str,
        breadcrumbs: List[dict],
    ) -> AsyncGenerator[ChunkEntity, None]:
        """Generate message entities for a channel."""
        url = f"{self.BASE_URL}/channels/{channel_id}/messages"
        params = {"limit": 100}

        while True:
            response = await self._get_with_auth(client, url, params)
            if not response:
                break

            for message in response:
                # Handle attachments first
                for attachment in message.get("attachments", []):
                    yield DiscordAttachmentEntity(
                        entity_id=attachment["id"],
                        file_id=attachment["id"],
                        name=attachment["filename"],
                        mime_type=attachment.get("content_type"),
                        size=attachment.get("size"),
                        download_url=attachment["url"],
                        message_id=message["id"],
                        channel_id=channel_id,
                        description=attachment.get("description"),
                        height=attachment.get("height"),
                        width=attachment.get("width"),
                        breadcrumbs=breadcrumbs,
                    )

                # Then handle the message itself
                created_at = datetime.fromisoformat(message["timestamp"].rstrip("Z"))
                edited_at = (
                    datetime.fromisoformat(message["edited_timestamp"].rstrip("Z"))
                    if message.get("edited_timestamp")
                    else None
                )

                yield DiscordMessageEntity(
                    entity_id=message["id"],
                    content=message["content"],
                    author_id=message["author"]["id"],
                    channel_id=channel_id,
                    created_at=created_at,
                    edited_at=edited_at,
                    pinned=message.get("pinned", False),
                    thread_id=message.get("thread", {}).get("id"),
                    breadcrumbs=breadcrumbs,
                )

            # Discord uses "before" pagination
            if len(response) < 100:
                break
            params["before"] = response[-1]["id"]

    async def _generate_thread_entities(
        self,
        client: httpx.AsyncClient,
        channel_id: str,
        breadcrumbs: List[dict],
    ) -> AsyncGenerator[DiscordThreadEntity, None]:
        """Generate thread entities for a channel."""
        url = f"{self.BASE_URL}/channels/{channel_id}/threads/archived/public"
        response = await self._get_with_auth(client, url)

        for thread in response.get("threads", []):
            created_at = datetime.fromisoformat(thread["thread_metadata"]["create_timestamp"].rstrip("Z"))
            yield DiscordThreadEntity(
                entity_id=thread["id"],
                name=thread["name"],
                parent_id=channel_id,
                owner_id=thread["owner_id"],
                created_at=created_at,
                archived=thread["thread_metadata"]["archived"],
                locked=thread["thread_metadata"]["locked"],
                message_count=thread["message_count"],
                content=thread["name"],
                breadcrumbs=breadcrumbs,
            )

    async def _generate_user_entities(
        self, client: httpx.AsyncClient, guild_id: str, guild_breadcrumb: dict
    ) -> AsyncGenerator[DiscordUserEntity, None]:
        """Generate user entities for a guild."""
        url = f"{self.BASE_URL}/guilds/{guild_id}/members"
        params = {"limit": 1000}

        while True:
            response = await self._get_with_auth(client, url, params)
            if not response:
                break

            for member in response:
                user = member["user"]
                created_at = datetime.fromtimestamp(
                    ((int(user["id"]) >> 22) + 1420070400000) / 1000
                )
                
                yield DiscordUserEntity(
                    entity_id=user["id"],
                    username=user["username"],
                    discriminator=user["discriminator"],
                    display_name=member.get("nick"),
                    avatar_url=f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png"
                    if user.get("avatar")
                    else None,
                    bot=user.get("bot", False),
                    created_at=created_at,
                    content=f"{user['username']}#{user['discriminator']}",
                    breadcrumbs=[guild_breadcrumb],
                )

            # Discord uses "after" pagination for members
            if len(response) < 1000:
                break
            params["after"] = response[-1]["user"]["id"]

    async def generate_entities(self) -> AsyncGenerator[ChunkEntity, None]:
        """Main entry point to generate all entities."""
        async with httpx.AsyncClient() as client:
            # First generate guild entities
            async for guild_entity in self._generate_guild_entities(client):
                yield guild_entity

                # Create guild breadcrumb
                guild_breadcrumb = {
                    "entity_id": guild_entity.entity_id,
                    "name": guild_entity.name,
                    "type": "guild",
                }

                # Generate channel entities for this guild
                async for channel_entity in self._generate_channel_entities(
                    client, guild_entity.entity_id, guild_breadcrumb
                ):
                    yield channel_entity

                    # Create channel breadcrumb
                    channel_breadcrumb = {
                        "entity_id": channel_entity.entity_id,
                        "name": channel_entity.name,
                        "type": "channel",
                    }
                    breadcrumbs = [guild_breadcrumb, channel_breadcrumb]

                    # Generate messages and threads for text channels
                    if channel_entity.type in ["0", "5"]:  # Text and announcement channels
                        async for message_entity in self._generate_message_entities(
                            client, channel_entity.entity_id, breadcrumbs
                        ):
                            yield message_entity

                        async for thread_entity in self._generate_thread_entities(
                            client, channel_entity.entity_id, breadcrumbs
                        ):
                            yield thread_entity

                # Generate user entities for this guild
                async for user_entity in self._generate_user_entities(
                    client, guild_entity.entity_id, guild_breadcrumb
                ):
                    yield user_entity 