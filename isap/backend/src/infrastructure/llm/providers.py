"""
LLM-абстракция (ADR-001).
Провайдеры: OpenAI/Gemini, Ollama, YandexGPT, GLM.
Переключение через LLM_PROVIDER в .env.
FallbackProvider автоматически переключается при ошибке.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx
from openai import AsyncOpenAI

from src.core.settings import settings


@dataclass
class LLMMessage:
    role: str   # system | user | assistant
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMProvider(ABC):
    """Базовый интерфейс для всех LLM-провайдеров."""

    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        ...


class OpenAIProvider(LLMProvider):
    """Провайдер OpenAI / Gemini (облако, OpenAI-совместимый API)."""

    def __init__(self):
        default_headers = {}
        if settings.openai_project_id:
            default_headers["OpenAI-Project"] = settings.openai_project_id
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            default_headers=default_headers or None,
        )
        self._model = settings.openai_model

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        kwargs = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature or settings.llm_temperature,
            "max_tokens": max_tokens or settings.llm_max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        return LLMResponse(
            content=choice.message.content or "",
            model=self._model,
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
        )


class YandexGPTProvider(LLMProvider):
    """Провайдер YandexGPT (API-ключ + folder_id)."""

    def __init__(self):
        self._api_key = settings.yandex_api_key
        self._folder_id = settings.yandex_folder_id
        self._model = settings.yandex_model or "yandexgpt"
        self._base_url = "https://llm.api.cloud.yandex.net"
        self._client = httpx.AsyncClient(timeout=120.0)

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        headers = {
            "Authorization": f"Api-Key {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "modelUri": f"gpt://{self._folder_id}/{self._model}",
            "completionOptions": {
                "stream": False,
                "temperature": temperature or settings.llm_temperature,
                "maxTokens": str(max_tokens or settings.llm_max_tokens),
            },
            "messages": [{"role": m.role, "text": m.content} for m in messages],
        }

        response = await self._client.post(
            f"{self._base_url}/fundamentals/v1/completion",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            content=data["result"]["alternatives"][0]["message"]["text"],
            model=self._model,
        )


class OllamaProvider(LLMProvider):
    """Провайдер Ollama (локальные модели)."""

    def __init__(self):
        self._base_url = settings.ollama_base_url
        self._model = settings.ollama_model
        self._client = httpx.AsyncClient(timeout=120.0)

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "options": {
                "temperature": temperature or settings.llm_temperature,
                "num_predict": max_tokens or settings.llm_max_tokens,
            },
            "stream": False,
        }
        if json_mode:
            payload["format"] = "json"

        response = await self._client.post(
            f"{self._base_url}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            content=data["message"]["content"],
            model=self._model,
        )


class GLMProvider(LLMProvider):
    """Провайдер GLM 4.5 (Zhipu AI)."""

    def __init__(self):
        self._api_key = settings.glm_api_key
        self._model = settings.glm_model or "glm-4"
        self._base_url = "https://open.bigmodel.cn/api/paas/v4"
        self._client = httpx.AsyncClient(timeout=120.0)

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature or settings.llm_temperature,
            "max_tokens": max_tokens or settings.llm_max_tokens,
        }

        response = await self._client.post(
            f"{self._base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=self._model,
            prompt_tokens=data.get("usage", {}).get("prompt_tokens", 0),
            completion_tokens=data.get("usage", {}).get("completion_tokens", 0),
        )


class FallbackProvider(LLMProvider):
    """Пробует основной провайдер, при ошибке — запасной."""

    def __init__(self, primary: LLMProvider, fallback: LLMProvider):
        self._primary = primary
        self._fallback = fallback

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        try:
            return await self._primary.complete(messages, temperature, max_tokens, json_mode)
        except Exception:
            return await self._fallback.complete(messages, temperature, max_tokens, json_mode)


def _create_provider(provider_type: str) -> LLMProvider:
    """Создаёт провайдер по типу."""
    providers = {
        "openai": OpenAIProvider,
        "ollama": OllamaProvider,
        "yandex": YandexGPTProvider,
        "glm": GLMProvider,
    }
    provider_class = providers.get(provider_type)
    if provider_class is None:
        raise ValueError(f"Unknown LLM provider: {provider_type}")
    return provider_class()


def get_llm_provider() -> LLMProvider:
    """Фабрика: возвращает нужный провайдер по конфигу."""
    primary = _create_provider(settings.llm_provider)
    if settings.llm_fallback_enabled:
        fallback_name = "ollama" if settings.llm_provider != "ollama" else "openai"
        try:
            fallback = _create_provider(fallback_name)
            return FallbackProvider(primary, fallback)
        except Exception:
            return primary
    return primary
