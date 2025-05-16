"""LLM provider base Abstract class."""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Union


class BaseLLMClient(ABC):
    """Abstract base class for all LLM clients."""

    @abstractmethod
    async def create_completion(
        self, messages: List[Dict], model: str, stream: bool = False, **kwargs
    ) -> Union[Dict, AsyncGenerator]:
        """Create a chat completion based on given messages."""
        pass
