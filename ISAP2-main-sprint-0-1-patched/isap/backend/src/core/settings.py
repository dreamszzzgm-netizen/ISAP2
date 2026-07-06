from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    # Приложение
    app_env: str = "development"
    app_secret_key: str = ""
    api_key: str = ""  # Единый ключ доступа. Пустая строка = auth отключена (dev).

    # База данных
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/isap"

    # LLM
    llm_provider: Literal["lmstudio", "openai", "ollama", "yandex", "glm"] = "lmstudio"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gemini-2.5-flash"
    openai_project_id: str = ""

    # LM Studio: OpenAI-compatible API, usually served from desktop app.
    # For backend inside Docker on Windows/Mac use http://host.docker.internal:1234/v1
    # For backend on host use http://localhost:1234/v1
    lmstudio_base_url: str = "http://host.docker.internal:1234/v1"
    lmstudio_api_key: str = "lm-studio"
    lmstudio_model: str = "local-model"
    # Embeddings are configured separately from chat completions.
    # Default: LM Studio OpenAI-compatible embeddings.
    embedding_provider: Literal["lmstudio", "openai", "ollama"] = "lmstudio"
    lmstudio_embedding_model: str = "text-embedding-nomic-embed-text-v1.5"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_batch_size: int = 100

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3:8b"
    ollama_embedding_model: str = "nomic-embed-text"
    yandex_api_key: str = ""
    yandex_folder_id: str = ""
    yandex_model: str = "yandexgpt"
    glm_api_key: str = ""
    glm_model: str = "glm-4"
    llm_fallback_enabled: bool = False

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection_name: str = "isap_knowledge"
    chroma_samples_collection: str = "isap_samples"

    # RAG
    chunk_size: int = 500        # токенов на фрагмент
    chunk_overlap: int = 50      # перекрытие между фрагментами
    retrieval_top_k: int = 5     # сколько фрагментов возвращать

    # Генерация документов
    llm_temperature: float = 0.2
    llm_max_tokens: int = 4096

    # Геокодирование (Яндекс)
    yandex_geocoder_api_key: str = ""

    # AI-ревью
    ai_review_enabled: bool = True
    ai_review_temperature: float = 0.3


settings = Settings()
