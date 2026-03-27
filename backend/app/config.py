from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Tome API"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:3000"

    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_fallback_provider: str = "ollama"
    llm_fallback_model: str = "llama3"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2048

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    max_upload_size_mb: int = 100
    top_k_chunks: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def books_index_path(self) -> Path:
        return self.data_dir / "books.json"


settings = Settings()
