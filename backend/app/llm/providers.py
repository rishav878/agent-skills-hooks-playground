import logging
from typing import Any

from app.core.config import settings
from app.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    def __init__(self, model_name: str = "", base_url: str = "") -> None:
        self._model = model_name or settings.ollama_model
        self._base_url = base_url or settings.ollama_base_url
        self._llm: Any = None

    @property
    def name(self) -> str:
        return f"ollama/{self._model}"

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        return await self.generate_chat([{"role": "human", "content": prompt}], **kwargs)

    async def generate_chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        if self._llm is None:
            try:
                from langchain_ollama import ChatOllama

                self._llm = ChatOllama(model=self._model, base_url=self._base_url)
            except ImportError:
                raise ImportError("langchain-ollama not installed") from None
        from langchain.schema import HumanMessage, SystemMessage

        langchain_messages = []
        for m in messages:
            role = m.get("role", "human")
            content = m.get("content", "")
            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            else:
                langchain_messages.append(HumanMessage(content=content))
        try:
            response = await self._llm.ainvoke(langchain_messages)
            return response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            logger.error("Ollama generation failed: %s", exc)
            return f"Error: {exc}"


class GeminiProvider(BaseLLMProvider):
    def __init__(self, model_name: str = "", api_key: str = "") -> None:
        self._model = model_name or "gemini-3.1-pro-preview"
        self._api_key = api_key or settings.google_api_key
        self._llm: Any = None

    @property
    def name(self) -> str:
        return f"gemini/{self._model}"

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        return await self.generate_chat([{"role": "human", "content": prompt}], **kwargs)

    async def generate_chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        if not self._api_key:
            return "Error: Google API key not configured"
        if self._llm is None:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI

                self._llm = ChatGoogleGenerativeAI(model=self._model, google_api_key=self._api_key)
            except ImportError:
                raise ImportError("langchain-google-genai not installed") from None
        from langchain.schema import HumanMessage, SystemMessage

        langchain_messages = []
        for m in messages:
            role = m.get("role", "human")
            content = m.get("content", "")
            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            else:
                langchain_messages.append(HumanMessage(content=content))
        try:
            response = await self._llm.ainvoke(langchain_messages)
            return response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            logger.error("Gemini generation failed: %s", exc)
            return f"Error: {exc}"


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, model_name: str = "", api_key: str = "") -> None:
        self._model = model_name or "gpt-3.5-turbo"
        self._api_key = api_key or settings.openai_api_key
        self._llm: Any = None

    @property
    def name(self) -> str:
        return f"openai/{self._model}"

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        return await self.generate_chat([{"role": "human", "content": prompt}], **kwargs)

    async def generate_chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        if not self._api_key:
            return "Error: OpenAI API key not configured"
        if self._llm is None:
            try:
                from langchain_openai import ChatOpenAI

                self._llm = ChatOpenAI(model=self._model, api_key=self._api_key)
            except ImportError:
                raise ImportError("langchain-openai not installed") from None
        from langchain.schema import HumanMessage, SystemMessage

        langchain_messages = []
        for m in messages:
            role = m.get("role", "human")
            content = m.get("content", "")
            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            else:
                langchain_messages.append(HumanMessage(content=content))
        try:
            response = await self._llm.ainvoke(langchain_messages)
            return response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            logger.error("OpenAI generation failed: %s", exc)
            return f"Error: {exc}"
