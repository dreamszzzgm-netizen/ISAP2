from src.api.routers.ai import _chat_model_name, _embedding_model_name
from src.core.settings import settings


def test_llm_provider_is_valid():
    valid = {"lmstudio", "openai", "ollama", "yandex", "glm"}
    assert settings.llm_provider in valid, f"Unexpected provider: {settings.llm_provider}"


def test_ai_config_helpers_return_model_names():
    assert _chat_model_name("lmstudio") == settings.lmstudio_model
    assert _embedding_model_name("lmstudio") == settings.lmstudio_embedding_model
