from abc import ABC, abstractmethod
from typing import Any


class BaseLLMProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str: ...

    @abstractmethod
    async def generate_chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str: ...
