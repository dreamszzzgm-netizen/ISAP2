"""Embedding providers.

Sprint 0.2 goal: separate chat LLM providers from embedding providers.
The application can use LM Studio for chat generation and a different provider
for embeddings without changing RAG code.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

try:
    from openai import AsyncOpenAI
except ModuleNotFoundError:  # optional until embedding generation is used
    AsyncOpenAI = None

from src.core.settings import settings


@dataclass(frozen=True)
class EmbeddingResponse:
    """Embedding result with provider metadata."""

    vectors: list[list[float]]
    model: str
    provider: str


class EmbeddingProvider(ABC):
    """Base interface for all embedding providers."""

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> EmbeddingResponse:
        """Create embeddings for a batch of texts."""
        ...

    async def embed_query(self, query: str) -> list[float]:
        """Create a single query embedding."""
        response = await self.embed_texts([query])
        return response.vectors[0]


class LMStudioEmbeddingProvider(EmbeddingProvider):
    """LM Studio embeddings through OpenAI-compatible API."""

    provider_name = "lmstudio"

    def __init__(self) -> None:
        self._client = None
        self._model = settings.lmstudio_embedding_model

    def _get_client(self):
        if AsyncOpenAI is None:
            raise RuntimeError("openai package is required for LM Studio embeddings")
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=settings.lmstudio_api_key or "lm-studio",
                base_url=settings.lmstudio_base_url,
            )
        return self._client

    async def embed_texts(self, texts: list[str]) -> EmbeddingResponse:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), settings.embedding_batch_size):
            batch = texts[i : i + settings.embedding_batch_size]
            response = await self._get_client().embeddings.create(
                model=self._model,
                input=batch,
            )
            vectors.extend([item.embedding for item in response.data])
        return EmbeddingResponse(vectors=vectors, model=self._model, provider=self.provider_name)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI-compatible cloud embeddings."""

    provider_name = "openai"

    def __init__(self) -> None:
        self._client = None
        self._model = settings.openai_embedding_model

    def _get_client(self):
        if AsyncOpenAI is None:
            raise RuntimeError("openai package is required for OpenAI-compatible embeddings")
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
            )
        return self._client

    async def embed_texts(self, texts: list[str]) -> EmbeddingResponse:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), settings.embedding_batch_size):
            batch = texts[i : i + settings.embedding_batch_size]
            response = await self._get_client().embeddings.create(
                model=self._model,
                input=batch,
            )
            vectors.extend([item.embedding for item in response.data])
        return EmbeddingResponse(vectors=vectors, model=self._model, provider=self.provider_name)


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama embeddings. Kept only as an alternative legacy provider."""

    provider_name = "ollama"

    def __init__(self) -> None:
        self._base_url = settings.ollama_base_url
        self._model = settings.ollama_embedding_model
        self._client = httpx.AsyncClient(timeout=60.0)

    async def embed_texts(self, texts: list[str]) -> EmbeddingResponse:
        vectors: list[list[float]] = []
        for text in texts:
            response = await self._client.post(
                f"{self._base_url}/api/embeddings",
                json={"model": self._model, "prompt": text},
            )
            response.raise_for_status()
            vectors.append(response.json()["embedding"])
        return EmbeddingResponse(vectors=vectors, model=self._model, provider=self.provider_name)


def get_embedding_provider() -> EmbeddingProvider:
    """Factory for embedding provider selected in settings."""
    providers: dict[str, type[EmbeddingProvider]] = {
        "lmstudio": LMStudioEmbeddingProvider,
        "openai": OpenAIEmbeddingProvider,
        "ollama": OllamaEmbeddingProvider,
    }
    provider_class = providers.get(settings.embedding_provider)
    if provider_class is None:
        raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")
    return provider_class()
