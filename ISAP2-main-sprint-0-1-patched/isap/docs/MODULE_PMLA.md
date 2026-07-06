# Модуль ПМЛА — Подробное описание

## Назначение

Модуль автоматической генерации, валидации и управления планами мероприятий по локализации и ликвидации последствий аварий (ПМЛА) на опасных производственных объектах (ОПО).

ПМЛА — обязательный документ для каждого ОПО, определяющий порядок действий персонала и аварийно-спасательных служб при возникновении аварий.

---

## Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                       │
│  Organizations │ Facilities │ Equipment │ Persons │ ПМЛА │
└────────────────────────┬────────────────────────────────┘
                         │ REST API
┌────────────────────────┴────────────────────────────────┐
│                   FastAPI Backend                        │
│                                                         │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ API层    │  │ Application  │  │ Infrastructure    │  │
│  │ 8 роутов │→ │ Services     │→ │ DB/LLM/RAG/PDF    │  │
│  └──────────┘  └──────────────┘  └───────────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
    ┌─────┴─────┐  ┌─────┴─────┐  ┌────┴────┐
    │ PostgreSQL │  │  Ollama   │  │ChromaDB │
    │   10 таблиц│  │  LLM 7B   │  │ RAG     │
    └───────────┘  └───────────┘  └─────────┘
```

---

## Стек технологий

| Компонент | Технология | Версия |
|-----------|-----------|--------|
| Backend | FastAPI + uvicorn | 0.111+ |
| ORM | SQLAlchemy (async) | 2.0+ |
| БД | PostgreSQL | 16 |
| Миграции | Alembic | 1.13+ |
| LLM | Ollama (qwen2.5-coder) | 7B |
| RAG | ChromaDB | 0.5+ |
| PDF | docx2pdf / fpdf2 | — |
| Frontend | React + Vite | 18.3 |
| Роутинг | React Router | 6+ |

---

## Структура базы данных

### Таблицы (10)

```
organizations          — эксплуатирующие организации
hazardous_facilities   — опасные производственные объекты (ОПО)
equipment              — оборудование ОПО
hazardous_substances   — опасные вещества
responsible_persons    — ответственные лица
documents              — сгенерированные документы (ПМЛА)
document_versions      — версии документов
regulatory_documents   — нормативные документы
calculation_results    — результаты расчётов
```

### Связи

```
organizations ──┬──< hazardous_facilities
                └──< responsible_persons

hazardous_facilities ──┬──< equipment
                       ├──< hazardous_substances
                       └──< documents

documents ──┬──< document_versions
            └──< calculation_results
```

---

## API — Полный каталог

### ПМЛА (6 эндпоинтов)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/pmla/generate` | Генерация ПМЛА |
| GET | `/api/v1/pmla/{id}/status` | Статус документа |
| POST | `/api/v1/pmla/{id}/review` | Ревью (утвердить/вернуть) |
| GET | `/api/v1/pmla/{id}/download` | Скачивание DOCX |
| GET | `/api/v1/pmla/{id}/download/pdf` | Скачивание PDF |
| GET | `/api/v1/pmla/methods/list` | Список расчётных методик |

**Пример запроса на генерацию:**

Режим 1 — автоматический сбор контекста из БД (рекомендуется):
```json
POST /api/v1/pmla/generate
{
  "facility_id": "uuid-объекта"
}
```

Режим 2 — ручная передача контекста (для переопределения данных):
```json
POST /api/v1/pmla/generate
{
  "facility_id": "uuid-объекта",
  "context": {
    "organization": {
      "name": "ООО \"Газпромнефть-Хантос\"",
      "inn": "8602060755",
      "address": "г. Тюмень, ул. Моторная, д. 8"
    },
    "facility": {
      "name": "Компрессорная станция \"Приобье\"",
      "facility_type": "Компрессорная станция",
      "hazard_class": 3,
      "reg_number": "РВ-86-00123"
    },
    "equipment": [
      {"name": "Компрессор К-500", "equipment_type": "Осевой компрессор"}
    ],
    "substances": [
      {"name": "Метан", "quantity_kg": 50000, "cas_number": "74-82-8"}
    ],
    "responsible_persons": [
      {"full_name": "Иванов И.И.", "position": "Начальник ПБ", "phone": "+7 (3452) 53-53-10"}
    ]
  }
}
```

**Пример запроса на ревью:**

Утверждение:
```json
POST /api/v1/pmla/{id}/review
{
  "reviewer_id": "uuid-ревьюера",
  "decision": "approved"
}
```

Возврат на доработку:
```json
POST /api/v1/pmla/{id}/review
{
  "reviewer_id": "uuid-ревьюера",
  "decision": "rejected",
  "comments": [
    {"section": "1.2", "reason": "Не указаны объёмы выбросов", "severity": "error"},
    {"section": "2.1", "reason": "Отсутствует номер телефона дежурной службы", "severity": "warning"}
  ]
}
```

### Организации (5 эндпоинтов)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/organizations/` | Создать |
| GET | `/api/v1/organizations/` | Список |
| GET | `/api/v1/organizations/{id}` | Получить |
| PUT | `/api/v1/organizations/{id}` | Обновить |
| DELETE | `/api/v1/organizations/{id}` | Удалить |

### Объекты ОПО (5 эндпоинтов)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/facilities/` | Создать |
| GET | `/api/v1/facilities/` | Список (`?organization_id=`) |
| GET | `/api/v1/facilities/{id}` | Получить |
| PUT | `/api/v1/facilities/{id}` | Обновить |
| DELETE | `/api/v1/facilities/{id}` | Удалить |

### Оборудование (5 эндпоинтов)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/equipment/` | Создать |
| GET | `/api/v1/equipment/` | Список (`?hazardous_facility_id=`) |
| GET | `/api/v1/equipment/{id}` | Получить |
| PUT | `/api/v1/equipment/{id}` | Обновить |
| DELETE | `/api/v1/equipment/{id}` | Удалить |

### Опасные вещества (5 эндпоинтов)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/substances/` | Создать |
| GET | `/api/v1/substances/` | Список (`?hazardous_facility_id=`) |
| GET | `/api/v1/substances/{id}` | Получить |
| PUT | `/api/v1/substances/{id}` | Обновить |
| DELETE | `/api/v1/substances/{id}` | Удалить |

### Ответственные лица (5 эндпоинтов)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/persons/` | Создать |
| GET | `/api/v1/persons/` | Список (`?organization_id=`) |
| GET | `/api/v1/persons/{id}` | Получить |
| PUT | `/api/v1/persons/{id}` | Обновить |
| DELETE | `/api/v1/persons/{id}` | Удалить |

### Нормативные документы (8 эндпоинтов)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/regulatory/` | Список |
| GET | `/api/v1/regulatory/{id}` | Детали |
| POST | `/api/v1/regulatory/` | Создать |
| PUT | `/api/v1/regulatory/{id}` | Обновить |
| POST | `/api/v1/regulatory/{id}/verify` | Верифицировать |
| GET | `/api/v1/regulatory/active/list` | Действующие |
| GET | `/api/v1/regulatory/disputed/list` | Спорные |
| GET | `/api/v1/regulatory/replaced/list` | Заменённые |

### Корпус знаний (2 эндпоинта)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/corpus/load` | Загрузка в ChromaDB |
| GET | `/api/v1/corpus/stats` | Статистика коллекции |

### Прочее

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/health` | Health check |

---

## Расчётный блок

### Методики

| ID | Название | Норматив |
|----|----------|----------|
| `tnt_equivalent_v1` | Метод эквивалента по ТНТ | РД 03-409-01 |
| `thermal_radiation_v1` | Модель теплового излучения | ГОСТ Р 12.3.047-98 |
| `toxic_dispersion_v1` | Модель рассеивания токсичных веществ | Атмосферная дисперсия |

### Валидация параметров

Каждая методика проверяет:
- Диапазоны массы и энергии
- Агрегатное состояние (газ/жидкость/твёрдое)
- Положительность значений
- Предупреждения при приближении к границам диапазонов

### Пример расчёта зоны взрыва

```python
from src.application.services.calculations.explosion_zone import ExplosionZoneCalculation
from src.application.services.calculations.types import ExplosionParams

params = ExplosionParams(
    substance_name="Метан",
    quantity_kg=50000,
    explosion_energy_mj=1000,
    physical_state="газ",
    confined=False,
)
result = ExplosionZoneCalculation.calculate(params)
# result.zone_radius_m = 8.3  (зона смертельного поражения)
```

---

## Пайплайн генерации ПМЛА

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Входные  │    │ Расчёты  │    │ RAG +    │    │ Валидация│    │ DOCX     │
│ данные   │ →  │ (взрыв,  │ →  │ LLM      │ →  │          │ →  │ экспорт  │
│ (context)│    │ тепло,   │    │ генерация│    │          │    │          │
│          │    │ токсика) │    │ секций   │    │          │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
      A               B               C               D               E
```

### Этапы

1. **A — Подготовка:** Формирование контекста из БД (org, facility, equipment, substances, persons) или из переданного JSON
2. **B — Расчётный блок:** Выполнение расчётов зон поражения (взрыв, тепловое излучение, токсическая дисперсия) на основе параметров веществ и оборудования
3. **C — Генерация текста (LLM + RAG):**
   - Для каждого раздела с `content_type: "llm"` выполняется поиск релевантных фрагментов в ChromaDB
   - Запрос формируется на основе типа объекта, класса опасности и наименований веществ
   - Найденные фрагменты (нормативы, примеры ПМЛА) передаются в промпт LLM как контекст
   - LLM генерирует текст раздела с учётом RAG-контекста и расчётных данных
4. **D — Валидация:** Проверка обязательных секций, контактов, нормативных ссылок, корректности числовых данных
5. **E — Экспорт:** Формирование DOCX через python-docx + Jinja2 шаблон

### Интеграция RAG в генерацию

```python
# Внутри EnhancedDocumentGenerator._generate_section_llm():
# 1. Формируется запрос на основе rag_query из шаблона раздела
rag_query = "аварии на {facility_type} с {substance_names}"

# 2. Поиск релевантных чанков в ChromaDB
rag_chunks = await retriever.retrieve(rag_query, top_k=5)

# 3. Фрагменты добавляются в промпт LLM
prompt = f"""
Ты — эксперт по промышленной безопасности.
Напиши раздел ПМЛА для {facility_type}.

Релевантные нормативы:
{rag_context}

Данные объекта:
{context}

Результаты расчётов:
{calc_placeholders}
"""
```

### Статусы документа

```
draft → processing → auto_validation_failed → pending_review → approved
                       ↓                           ↓
                    (LLM ошибка)               rejected
```

---

## RAG — Поиск по корпусу знаний

### Компоненты

| Компонент | Назначение |
|-----------|-----------|
| `DocumentLoader` | Загрузка PDF, TXT, DOCX |
| `Chunker` | Разбивка на фрагменты (500 слов, overlap 50) |
| `Embedder` | Векторизация (Ollama nomic-embed-text или OpenAI) |
| `VectorStore` | Хранение в ChromaDB (косинусное сходство) |
| `Retriever` | Высокоуровневый поиск (top-k=5) |

### Загрузка корпуса

```bash
# Через API
curl -X POST http://localhost:8000/api/v1/corpus/load

# Через CLI
cd backend
python -m scripts.load_corpus
```

### Источники данных

- Нормативные документы из БД (автоматически)
- Утверждённые ПМЛА из БД (автоматически)
- Файлы из `backend/data/corpus/` (txt/pdf/docx)
- `pmla_content.txt` (эталонный документ)

---

## Фронтенд

### Страницы

| Страница | Роут | Назначение |
|----------|------|-----------|
| Главная | `/` | Дашборд со статистикой |
| Организации | `/organizations` | CRUD-таблица |
| Ответственные лица | `/persons` | CRUD + фильтр по org |
| Объекты ОПО | `/facilities` | Список + фильтр по org |
| Карточка ОПО | `/facilities/:id` | Детали + табы Equipment/Substances |
| Генерация ПМЛА | `/pmla` | Выбор org → facility → генерация |
| Нормативы | `/regulatory` | Список нормативных документов |

### Навигация

Боковая панель (sidebar) с ссылками на все разделы. Активная страница подсвечивается.

### Генерация ПМЛА во фронтенде

1. Выбрать организацию
2. Выбрать объект ОПО
3. Нажать «Сгенерировать ПМЛА»
4. Контекст автоматически собирается из БД (equipment, substances, persons)
5. Дождаться статуса `pending_review`
6. Утвердить или вернуть
7. Скачать DOCX или PDF

---

## Конфигурация

### Переменные окружения (.env)

```env
# База данных
DATABASE_URL=postgresql+asyncpg://isap_user:isap_password@localhost:5432/isap

# LLM
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b

# ChromaDB
CHROMA_HOST=localhost
CHROMA_PORT=8001
CHROMA_COLLECTION_NAME=isap_knowledge

# RAG
CHUNK_SIZE=500
CHUNK_OVERLAP=50
RETRIEVAL_TOP_K=5

# PDF
# docx2pdf использует MS Word (если установлен)
# fpdf2 — fallback без внешних зависимостей
```

### Сервисы

| Сервис | Порт | Назначение |
|--------|------|-----------|
| PostgreSQL | 5432 | Основная БД |
| Ollama | 11434 | LLM (локально) |
| ChromaDB | 8001 | Векторная БД (опционально) |
| FastAPI | 8000 | Backend API |
| React/Vite | 3000 | Frontend |

---

## Тестирование

### Запуск тестов

```bash
cd backend
python -m pytest tests/ -v
```

### Покрытие

| Модуль | Тестов | Описание |
|--------|--------|----------|
| Расчёты | 24 | Explosion, Thermal, Toxic, Registry |
| Валидация | 18 | Границы диапазонов, предупреждения |
| Репозитории | 14 | CRUD Base + FacilityWithData |
| API | 22 | Все роуты через dependency override |
| **Итого** | **77** | |

---

## Деплой через Docker

```bash
# Полный запуск
docker-compose up --build

# Только БД и ChromaDB
docker-compose up db chromadb -d

# Применение миграций
docker-compose exec backend alembic upgrade head

# Загрузка нормативов
docker-compose exec backend python -m scripts.load_regulatory_data

# Загрузка корпуса
docker-compose exec backend python -m scripts.load_corpus
```

---

## Ключевые файлы

```
backend/
├── src/
│   ├── api/routers/          # 8 API-роутеров
│   ├── application/services/ # Бизнес-логика + расчёты
│   ├── infrastructure/
│   │   ├── database/models.py   # 10 ORM-моделей
│   │   ├── repositories/        # 7 репозиториев
│   │   ├── rag/pipeline.py      # RAG-компоненты
│   │   ├── rag/corpus_loader.py # Загрузка корпуса
│   │   ├── llm/providers.py     # OpenAI/Ollama
│   │   └── pdf/converter.py     # DOCX→PDF
│   └── core/settings.py     # Конфигурация
├── tests/                    # 77 тестов
├── scripts/                  # CLI-скрипты
├── alembic/                  # 4 миграции
└── templates/pmla/           # Шаблоны документов

frontend/
├── src/
│   ├── api.js               # API-клиенты (6 модулей)
│   ├── pages/               # 7 страниц
│   ├── App.jsx              # Маршрутизация
│   └── index.css            # Стили
└── package.json
```
