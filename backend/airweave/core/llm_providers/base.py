"""LLM provider base Abstract class"""

from abc import ABC, abstractmethod
from typing import List, Dict, Union, AsyncGenerator


class BaseLLMClient(ABC):
    @abstractmethod
    async def create_completion(
        self,
        messages: List[Dict],
        model: str,
        stream: bool = False,
        **kwargs
    ) -> Union[Dict, AsyncGenerator]:
        """Create a chat completion based on given messages."""
        pass