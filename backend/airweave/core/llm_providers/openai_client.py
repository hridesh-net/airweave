"""OpenAI Client to handle request for OpenAI"""

from openai import AsyncOpenAI
from .base import BaseLLMClient
from openai.types.chat import ChatCompletionChunk
from typing import List, Dict, AsyncGenerator, Union

class OpenAIClient(BaseLLMClient):
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def create_completion(
        self,
        messages: List[Dict],
        model: str,
        stream: bool = False,
        **kwargs
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        return await self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=stream,
            **kwargs
        )