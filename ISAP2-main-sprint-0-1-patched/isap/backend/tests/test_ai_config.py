from src.api.routers.ai import _chat_model_name, _embedding_model_name
from src.core.settings import settings


def test_default_ai_settings_are_lmstudio_first():
    assert settings.llm_provider == "lmstudio"
    assert settings.embedding_provider == "lmstudio"


def test_ai_config_helpers_return_model_names():
    assert _chat_model_name() == settings.lmstudio_model
    assert _embedding_model_name() == settings.lmstudio_embedding_model
