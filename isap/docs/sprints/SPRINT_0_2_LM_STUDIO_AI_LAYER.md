# Sprint 0.2 — LM Studio AI Layer Cleanup

## Цель

Привести AI/LLM слой проекта к реальной целевой схеме:

```text
Backend → OpenAI-compatible API → LM Studio
```

Ollama остаётся как альтернативный legacy-провайдер, но не является основным сценарием разработки.

## Что изменено

### 1. Разделены chat LLM и embeddings

До Sprint 0.2 RAG `Embedder` выбирал embeddings на основе `LLM_PROVIDER`. Это мешало использовать разные модели для генерации текста и векторизации.

Теперь есть отдельная настройка:

```env
LLM_PROVIDER=lmstudio
EMBEDDING_PROVIDER=lmstudio
```

Это позволит в будущем использовать, например:

```env
LLM_PROVIDER=lmstudio
EMBEDDING_PROVIDER=openai
```

или

```env
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=lmstudio
```

### 2. Добавлен модуль `infrastructure/embeddings`

Новые файлы:

```text
backend/src/infrastructure/embeddings/__init__.py
backend/src/infrastructure/embeddings/providers.py
```

Провайдеры:

- `LMStudioEmbeddingProvider`
- `OpenAIEmbeddingProvider`
- `OllamaEmbeddingProvider`

### 3. Обновлён RAG Embedder

`backend/src/infrastructure/rag/pipeline.py` больше не содержит прямой логики OpenAI/Ollama embeddings.

Теперь он использует единый интерфейс:

```python
get_embedding_provider()
```

### 4. Добавлены AI diagnostics endpoints

```http
GET /api/v1/ai/config
GET /api/v1/ai/health
GET /api/v1/ai/embeddings/health
```

`/config` возвращает только не-секретные настройки.

### 5. Обновлены `.env.example` и `docker-compose.yml`

Добавлены:

```env
EMBEDDING_PROVIDER=lmstudio
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_BATCH_SIZE=100
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

### 6. Обновлён README

README теперь описывает LM Studio как основной способ подключения локальной модели.

## Проверка

Backend tests:

```text
254 passed, 11 warnings
```

## Следующий спринт

Sprint 0.3 — разгрузка большого `pmla.py` и выделение `PmlaGenerationService`.
