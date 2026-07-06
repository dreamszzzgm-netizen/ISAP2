"""AI diagnostics and settings endpoints."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.settings import settings

router = APIRouter()

AI_SETTINGS_FILE = Path(__file__).parent.parent.parent.parent / "ai_settings.json"


class AiSettingsUpdate(BaseModel):
    llm_provider: str | None = None
    lmstudio_model: str | None = None
    lmstudio_base_url: str | None = None
    lmstudio_api_key: str | None = None
    lmstudio_embedding_model: str | None = None
    openai_model: str | None = None
    openai_base_url: str | None = None
    openai_api_key: str | None = None
    openai_embedding_model: str | None = None
    ollama_model: str | None = None
    ollama_base_url: str | None = None
    ollama_embedding_model: str | None = None
    embedding_provider: str | None = None
    llm_fallback_enabled: bool | None = None


def _load_custom_settings() -> dict:
    if AI_SETTINGS_FILE.exists():
        try:
            return json.loads(AI_SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _get_setting(name: str, default=None):
    custom = _load_custom_settings()
    if name in custom:
        return custom[name]
    return getattr(settings, name, default)


def _save_custom_settings(updates: dict) -> dict:
    current = _load_custom_settings()
    for key, value in updates.items():
        if value is not None:
            current[key] = value
    AI_SETTINGS_FILE.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return current


@router.get("/config")
async def ai_config() -> dict:
    llm_provider = _get_setting("llm_provider", "unknown")
    return {
        "llm": {
            "provider": llm_provider,
            "model": _chat_model_name(llm_provider),
            "base_url": _safe_base_url(llm_provider),
            "fallback_enabled": _get_setting("llm_fallback_enabled", False),
        },
        "embeddings": {
            "provider": _get_setting("embedding_provider", llm_provider),
            "model": _embedding_model_name(_get_setting("embedding_provider", llm_provider)),
        },
        "rag": {
            "chroma_host": _get_setting("chroma_host", "localhost"),
            "chroma_port": _get_setting("chroma_port", 8001),
            "collection": _get_setting("chroma_collection_name", "isap_knowledge"),
            "top_k": _get_setting("retrieval_top_k", 5),
        },
    }


@router.get("/settings")
async def get_ai_settings() -> dict:
    custom = _load_custom_settings()
    llm_provider = _get_setting("llm_provider", "lmstudio")
    return {
        "llm_provider": llm_provider,
        "lmstudio_model": _get_setting("lmstudio_model", "local-model"),
        "lmstudio_base_url": _get_setting("lmstudio_base_url", "http://host.docker.internal:1234/v1"),
        "lmstudio_api_key": _get_setting("lmstudio_api_key", "lm-studio"),
        "lmstudio_embedding_model": _get_setting("lmstudio_embedding_model", "text-embedding-nomic-embed-text-v1.5"),
        "openai_model": _get_setting("openai_model", "gemini-2.5-flash"),
        "openai_base_url": _get_setting("openai_base_url", "https://api.openai.com/v1"),
        "openai_api_key": _get_setting("openai_api_key", ""),
        "openai_embedding_model": _get_setting("openai_embedding_model", "text-embedding-3-small"),
        "ollama_model": _get_setting("ollama_model", "llama3:8b"),
        "ollama_base_url": _get_setting("ollama_base_url", "http://localhost:11434"),
        "ollama_embedding_model": _get_setting("ollama_embedding_model", "nomic-embed-text"),
        "embedding_provider": _get_setting("embedding_provider", llm_provider),
        "llm_fallback_enabled": _get_setting("llm_fallback_enabled", False),
        "_custom_fields": list(custom.keys()),
    }


@router.post("/settings")
async def update_ai_settings(data: AiSettingsUpdate) -> dict:
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No settings to update")
    _save_custom_settings(updates)
    return {"status": "ok", "updated": list(updates.keys())}


@router.get("/health")
async def ai_health() -> dict:
    provider_name = _get_setting("llm_provider", "unknown")
    try:
        from src.infrastructure.llm.providers import LLMMessage, get_llm_provider

        provider = get_llm_provider()
        response = await provider.complete(
            [LLMMessage(role="user", content="Ответь одним словом: ok")],
            temperature=0.0,
            max_tokens=16,
        )
        return {
            "status": "ok",
            "provider": provider_name,
            "model": response.model,
        }
    except Exception as exc:  # noqa: BLE001 - diagnostic endpoint
        return {
            "status": "error",
            "provider": provider_name,
            "model": _chat_model_name(provider_name),
            "error": exc.__class__.__name__,
            "message": str(exc),
        }


@router.get("/embeddings/health")
async def embeddings_health() -> dict:
    embedding_provider = _get_setting("embedding_provider", _get_setting("llm_provider", "unknown"))
    try:
        from src.infrastructure.embeddings.providers import get_embedding_provider

        provider = get_embedding_provider()
        response = await provider.embed_texts(["Проверка эмбеддингов ISAP"])
        dimension = len(response.vectors[0]) if response.vectors else 0
        return {
            "status": "ok",
            "provider": response.provider,
            "model": response.model,
            "dimension": dimension,
        }
    except ModuleNotFoundError:
        return {
            "status": "not_configured",
            "provider": embedding_provider,
            "model": _embedding_model_name(embedding_provider),
            "message": "Embedding provider module is not installed in this backend revision.",
        }
    except Exception as exc:  # noqa: BLE001 - diagnostic endpoint
        return {
            "status": "error",
            "provider": embedding_provider,
            "model": _embedding_model_name(embedding_provider),
            "error": exc.__class__.__name__,
            "message": str(exc),
        }


def _chat_model_name(provider: str | None = None) -> str:
    provider = provider or _get_setting("llm_provider", "unknown")
    if provider == "lmstudio":
        return _get_setting("lmstudio_model", "local-model")
    if provider == "openai":
        return _get_setting("openai_model", "")
    if provider == "ollama":
        return _get_setting("ollama_model", "")
    if provider == "yandex":
        return _get_setting("yandex_model", "")
    if provider == "glm":
        return _get_setting("glm_model", "")
    return "unknown"


def _embedding_model_name(provider: str | None = None) -> str:
    provider = provider or _get_setting("embedding_provider", _get_setting("llm_provider", "unknown"))
    if provider == "lmstudio":
        return _get_setting("lmstudio_embedding_model", "text-embedding-nomic-embed-text-v1.5")
    if provider == "openai":
        return _get_setting("openai_embedding_model", "text-embedding-3-small")
    if provider == "ollama":
        return _get_setting("ollama_embedding_model", "nomic-embed-text")
    return "unknown"


def _safe_base_url(provider: str | None = None) -> str:
    provider = provider or _get_setting("llm_provider", "unknown")
    if provider == "lmstudio":
        return _get_setting("lmstudio_base_url", "http://host.docker.internal:1234/v1")
    if provider == "openai":
        return _get_setting("openai_base_url", "")
    if provider == "ollama":
        return _get_setting("ollama_base_url", "")
    return ""
