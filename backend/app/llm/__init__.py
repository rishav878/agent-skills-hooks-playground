from typing import Any

from app.llm.base import BaseLLMProvider


def create_llm_provider(provider_name: str = "", **kwargs: Any) -> BaseLLMProvider:
    from app.core.config import settings
    from app.llm.providers import GeminiProvider, OllamaProvider, OpenAIProvider

    name = provider_name or settings.llm_provider
    if name == "ollama":
        return OllamaProvider(model_name=kwargs.get("model", settings.ollama_model))
    if name == "gemini":
        return GeminiProvider(api_key=kwargs.get("api_key", settings.google_api_key))
    if name == "openai":
        return OpenAIProvider(api_key=kwargs.get("api_key", settings.openai_api_key))
    raise ValueError(f"Unknown LLM provider: {name}")
