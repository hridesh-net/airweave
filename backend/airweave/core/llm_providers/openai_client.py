"""OpenAI client to handle requests for OpenAI."""

from typing import AsyncGenerator, Dict, List

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionChunk

from .base import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    """Client implementation to interact with OpenAI chat completion API."""

    def __init__(self, api_key: str):
        """Initialize the OpenAI client with the given API key."""
        self.client = AsyncOpenAI(api_key=api_key)

    async def create_completion(
        self, messages: List[Dict], model: str, stream: bool = False, **kwargs
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Create a streaming or non-streaming chat completion using OpenAI."""
        return await self.client.chat.completions.create(
            model=model, messages=messages, stream=stream, **kwargs
        )
