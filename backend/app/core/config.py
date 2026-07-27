from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = "sqlite+aiosqlite:///./agent_playground.db"

    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "deepseek-r1:7b"
    google_api_key: str = ""
    openai_api_key: str = ""

    chroma_persist_directory: str = "./chroma_data"
    embedding_provider: str = "sentence-transformers"
    embedding_model: str = "all-MiniLM-L6-v2"
    vectorstore_collection_prefix: str = "skill_"

    cors_origins: str = "http://localhost:5173,http://localhost:8501"

    api_key: str = "dev-key-change-me"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def database_url_async(self) -> str:
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if self.database_url.startswith("postgresql+psycopg2://"):
            return self.database_url.replace(
                "postgresql+psycopg2://", "postgresql+asyncpg://", 1
            )
        return self.database_url

    @property
    def database_url_sync(self) -> str:
        if self.database_url.startswith("sqlite+aiosqlite"):
            return self.database_url.replace("+aiosqlite", "")
        if self.database_url.startswith("postgresql+asyncpg"):
            return self.database_url.replace("+asyncpg", "+psycopg2")
        return self.database_url


settings = Settings()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
