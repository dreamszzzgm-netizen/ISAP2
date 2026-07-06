from src.infrastructure.embeddings.providers import (
    LMStudioEmbeddingProvider,
    get_embedding_provider,
)


def test_get_embedding_provider_defaults_to_lmstudio():
    provider = get_embedding_provider()
    assert isinstance(provider, LMStudioEmbeddingProvider)
