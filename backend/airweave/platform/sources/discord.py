"""Discord source implementation."""

import logging
from datetime import datetime
from typing import AsyncGenerator, Optional

import httpx
import tenacity
from tenacity import retry_if_exception_type, stop_after_attempt, wait_exponential

from airweave.platform.entities._base import ChunkEntity
from airweave.platform.entities.discord import (
    Breadcrumb,
    DiscordAttachmentEntity,
    DiscordChannelEntity,
    DiscordMessageEntity,
    DiscordUserEntity,
)
from airweave.platform.sources._base import BaseSource, source
from airweave.platform.sources.auth import AuthType

logger = logging.getLogger(__name__)


@source("Discord", "discord", AuthType.oauth2_with_refresh)
class DiscordSource(BaseSource):
    """Discord source implementation."""

    BASE_URL = "https://discord.com/api/v10"

    @classmethod
    async def create(cls, access_token: str) -> "DiscordSource":
        """Create a new source instance with authentication."""
        instance = cls()
        instance.access_token = access_token
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
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    async def _generate_user_entities(
        self, client: httpx.AsyncClient
    ) -> AsyncGenerator[DiscordUserEntity, None]:
        """Generate user entities."""
        url = f"{self.BASE_URL}/users/@me"
        user_data = await self._get_with_auth(client, url)

        yield DiscordUserEntity(
            entity_id=user_data["id"],
            username=user_data["username"],
            discriminator=user_data["discriminator"],
            avatar=user_data.get("avatar"),
            bot=user_data.get("bot", False),
            email=user_data.get("email"),
        )

    async def _generate_channel_entities(
        self, client: httpx.AsyncClient
    ) -> AsyncGenerator[DiscordChannelEntity, None]:
        """Generate channel entities."""
        # First get guilds the user has access to
        guilds_url = f"{self.BASE_URL}/users/@me/guilds"
        guilds_data = await self._get_with_auth(client, guilds_url)

        for guild in guilds_data:
            guild_id = guild["id"]
            channels_url = f"{self.BASE_URL}/guilds/{guild_id}/channels"

            try:
                channels_data = await self._get_with_auth(client, channels_url)

                for channel in channels_data:
                    yield DiscordChannelEntity(
                        entity_id=channel["id"],
                        name=channel["name"],
                        type=channel["type"],
                        guild_id=guild_id,
                        position=channel.get("position"),
                        topic=channel.get("topic"),
                        nsfw=channel.get("nsfw", False),
                        parent_id=channel.get("parent_id"),
                        breadcrumbs=[
                            Breadcrumb(entity_id=guild["id"], name=guild["name"], type="guild")
                        ],
                    )
            except httpx.HTTPError as e:
                logger.error(f"Error fetching channels for guild {guild_id}: {str(e)}")
                continue

    async def _generate_message_entities(
        self, client: httpx.AsyncClient, channel: DiscordChannelEntity
    ) -> AsyncGenerator[ChunkEntity, None]:
        """Generate message entities for a channel."""
        url = f"{self.BASE_URL}/channels/{channel.entity_id}/messages"
        params = {"limit": 100}

        try:
            while True:
                messages_data = await self._get_with_auth(client, url, params)

                if not messages_data:
                    break

                for message in messages_data:
                    # Handle attachments first
                    for attachment in message.get("attachments", []):
                        yield DiscordAttachmentEntity(
                            entity_id=attachment["id"],
                            file_id=attachment["id"],
                            name=attachment["filename"],
                            size=attachment["size"],
                            mime_type=attachment.get("content_type"),
                            download_url=attachment["url"],
                            height=attachment.get("height"),
                            width=attachment.get("width"),
                            breadcrumbs=[
                                Breadcrumb(entity_id=channel.guild_id, name="guild", type="guild"),
                                Breadcrumb(
                                    entity_id=channel.entity_id, name=channel.name, type="channel"
                                ),
                            ],
                        )

                    # Then handle the message itself
                    yield DiscordMessageEntity(
                        entity_id=message["id"],
                        content=message["content"],
                        author_id=message["author"]["id"],
                        channel_id=channel.entity_id,
                        guild_id=channel.guild_id,
                        created_at=datetime.fromisoformat(message["timestamp"].rstrip("Z")),
                        edited_at=datetime.fromisoformat(message["edited_timestamp"].rstrip("Z"))
                        if message.get("edited_timestamp")
                        else None,
                        pinned=message.get("pinned", False),
                        mention_everyone=message.get("mention_everyone", False),
                        attachments=[att["id"] for att in message.get("attachments", [])],
                        breadcrumbs=[
                            Breadcrumb(entity_id=channel.guild_id, name="guild", type="guild"),
                            Breadcrumb(
                                entity_id=channel.entity_id, name=channel.name, type="channel"
                            ),
                        ],
                    )

                # Handle pagination
                if len(messages_data) < 100:
                    break

                params["before"] = messages_data[-1]["id"]

        except httpx.HTTPError as e:
            logger.error(f"Error fetching messages for channel {channel.entity_id}: {str(e)}")

    async def generate_entities(self) -> AsyncGenerator[ChunkEntity, None]:
        """Main entry point to generate all entities."""
        async with httpx.AsyncClient() as client:
            # First generate user entities
            async for user_entity in self._generate_user_entities(client):
                yield user_entity

            # Then generate channel entities
            async for channel_entity in self._generate_channel_entities(client):
                yield channel_entity

                # For each channel, generate message entities
                async for message_entity in self._generate_message_entities(client, channel_entity):
                    yield message_entity
