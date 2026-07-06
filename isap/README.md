# Industrial Safety AI Platform (ISAP)

Платформа автоматизации промышленной безопасности на основе AI.

## Быстрый старт

### 1. Клонировать репозиторий и настроить окружение

```bash
cp .env.example .env
# Отредактировать .env — указать LLM_PROVIDER и ключи
```

### 2. Запустить через Docker Compose

```bash
docker-compose up --build
```

Сервисы:
- Backend API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs
- Frontend: http://localhost:3000
- ChromaDB: http://localhost:8001

### 3. Применить миграции БД

```bash
docker-compose exec backend alembic upgrade head
```

### 4. Локальная разработка (без Docker)

```bash
cd backend
pip install -e ".[dev]"

# Запустить PostgreSQL и ChromaDB отдельно (или через docker-compose)
docker-compose up db chromadb -d

# Запустить FastAPI
uvicorn src.main:app --reload
```

---

## Структура проекта

```
isap/
├── backend/
│   ├── src/
│   │   ├── core/           # Конфигурация (settings.py)
│   │   ├── domain/         # Доменные модели (Organization, Facility, Document)
│   │   ├── infrastructure/ # БД, LLM, RAG
│   │   │   ├── llm/        # OpenAI и LLm studio провайдеры (ADR-001)
│   │   │   └── rag/        # DocumentLoader, Chunker, Embedder, VectorStore
│   │   ├── application/    # Бизнес-логика (DocumentGenerator)
│   │   └── api/            # FastAPI роутеры
│   ├── templates/
│   │   └── pmla/           # Шаблоны ПМЛА (structure.json + Jinja2)
│   ├── alembic/            # Миграции БД
│   └── tests/
├── frontend/               # React
├── docs/adr/               # Архитектурные решения
└── docker-compose.yml
```

---

## LLM провайдеры

### Ollama (локально, рекомендуется для старта)

```bash
# Установить Ollama: https://ollama.ai
ollama pull qwen2.5:14b
ollama pull nomic-embed-text
```

В `.env`:
```
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b
```

### OpenAI (облако)

```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
```

---

## Тест генерации ПМЛА

После запуска — открыть http://localhost:8000/docs и выполнить запрос:

```
POST /api/v1/documents/generate
```

```json
{
  "facility_id": "00000000-0000-0000-0000-000000000001",
  "document_type": "pmla",
  "context": {
    "organization": {
      "name": "АО «Хлебокомбинат»",
      "inn": "1444507155",
      "address": "г. Якутск, ул. Очичкенко, д.17"
    },
    "facility": {
      "name": "Сеть газопотребления Хлебозавода №2",
      "reg_number": "А01-0001-0005",
      "hazard_class": 3,
      "facility_type": "Сеть газопотребления"
    },
    "equipment": [
      {
        "name": "Подводящий газопровод высокого давления",
        "equipment_type": "Газопровод",
        "specifications": {"length_m": 95, "diameter_mm": 89, "pressure_mpa": 0.6}
      },
      {
        "name": "Водогрейный котел ROSSEN RSD 1000",
        "equipment_type": "Котёл",
        "specifications": {"quantity": 2, "power_mw": 1, "pressure_mpa": 0.8}
      }
    ],
    "substances": [
      {
        "name": "Природный газ (метан)",
        "quantity_kg": 800,
        "hazard_properties": {"physical_state": "газ", "hazard_class_gost": 4}
      }
    ],
    "responsible_persons": [
      {"full_name": "Иванова С.Т.", "position": "Директор", "phone": "+7 (4112) 43-33-01"}
    ]
  }
}
```

---

## Документация проекта

- [PROJECT_CHARTER.md](docs/PROJECT_CHARTER.md)
- [VISION.md](docs/VISION.md)
- [MVP_SCOPE.md](docs/MVP_SCOPE.md)
- [ADR-001](docs/adr/ADR-001.md) — RAG-фреймворк
- [ADR-002](docs/adr/ADR-002.md) — Модель данных
- [ADR-003](docs/adr/ADR-003.md) — Шаблоны документов

## Smart Import Center

Добавлен единый механизм умного импорта Excel/CSV.

Поддерживаемые первые профили:

- `fire_departments` — пожарные подразделения;
- `pasf_units` — ПАСФ / АСФ;
- `pmla_questionnaire` — анкета генерации ПМЛА.

Основные endpoints:

```http
GET  /api/v1/imports/profiles
POST /api/v1/imports/{import_type}/preview
GET  /api/v1/imports/jobs/{job_id}
GET  /api/v1/imports/jobs/{job_id}/rows
POST /api/v1/imports/jobs/{job_id}/confirm
```

Подробнее: `docs/SMART_IMPORT_CENTER.md`.

## Frontend Migration

Начиная с этого патча frontend переведён с Vite/React на Next.js + TypeScript + Tailwind + shadcn/ui.

Правильная схема интеграции:

```text
Next.js frontend → FastAPI backend → PostgreSQL
```

Frontend не использует Prisma/SQLite и не имеет прямого доступа к БД.

Настройка API backend:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Подробнее: `docs/FRONTEND_MIGRATION.md`.
