"""AI service health and configuration endpoints."""
from fastapi import APIRouter

from src.core.settings import settings
from src.infrastructure.embeddings.providers import get_embedding_provider
from src.infrastructure.llm.providers import LLMMessage, get_llm_provider

router = APIRouter()


@router.get("/config")
async def ai_config() -> dict:
    """Return non-secret AI configuration for UI diagnostics."""
    return {
        "llm": {
            "provider": settings.llm_provider,
            "model": _chat_model_name(),
            "base_url": _safe_base_url(),
            "fallback_enabled": settings.llm_fallback_enabled,
        },
        "embeddings": {
            "provider": settings.embedding_provider,
            "model": _embedding_model_name(),
        },
        "rag": {
            "chroma_host": settings.chroma_host,
            "chroma_port": settings.chroma_port,
            "collection": settings.chroma_collection_name,
            "top_k": settings.retrieval_top_k,
        },
    }


@router.get("/health")
async def ai_health() -> dict:
    """Check configured chat LLM provider without exposing secrets."""
    provider = get_llm_provider()
    try:
        response = await provider.complete(
            [LLMMessage(role="user", content="Ответь одним словом: ok")],
            temperature=0.0,
            max_tokens=16,
        )
        return {
            "status": "ok",
            "provider": settings.llm_provider,
            "model": response.model,
        }
    except Exception as exc:
        return {
            "status": "error",
            "provider": settings.llm_provider,
            "model": _chat_model_name(),
            "error": exc.__class__.__name__,
            "message": str(exc),
        }


@router.get("/embeddings/health")
async def embeddings_health() -> dict:
    """Check configured embedding provider independently from chat LLM."""
    provider = get_embedding_provider()
    try:
        response = await provider.embed_texts(["Проверка эмбеддингов ISAP"])
        dimension = len(response.vectors[0]) if response.vectors else 0
        return {
            "status": "ok",
            "provider": response.provider,
            "model": response.model,
            "dimension": dimension,
        }
    except Exception as exc:
        return {
            "status": "error",
            "provider": settings.embedding_provider,
            "model": _embedding_model_name(),
            "error": exc.__class__.__name__,
            "message": str(exc),
        }


def _chat_model_name() -> str:
    if settings.llm_provider == "lmstudio":
        return settings.lmstudio_model
    if settings.llm_provider == "openai":
        return settings.openai_model
    if settings.llm_provider == "ollama":
        return settings.ollama_model
    if settings.llm_provider == "yandex":
        return settings.yandex_model
    if settings.llm_provider == "glm":
        return settings.glm_model
    return "unknown"


def _embedding_model_name() -> str:
    if settings.embedding_provider == "lmstudio":
        return settings.lmstudio_embedding_model
    if settings.embedding_provider == "openai":
        return settings.openai_embedding_model
    if settings.embedding_provider == "ollama":
        return settings.ollama_embedding_model
    return "unknown"


def _safe_base_url() -> str:
    if settings.llm_provider == "lmstudio":
        return settings.lmstudio_base_url
    if settings.llm_provider == "openai":
        return settings.openai_base_url
    if settings.llm_provider == "ollama":
        return settings.ollama_base_url
    return ""
