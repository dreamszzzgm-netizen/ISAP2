"""Общие фикстуры для тестов — отключают auth middleware."""
import os

# Отключаем API Key auth для всех тестов (middleware пропускает запросы при пустом ключе)
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/isap_test")
os.environ["API_KEY"] = ""
os.environ.setdefault("LLM_PROVIDER", "lmstudio")
os.environ.setdefault("LLM_FALLBACK_ENABLED", "false")
