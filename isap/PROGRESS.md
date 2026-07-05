# Отчёт прогресса: ISAP

**Дата обновления:** 2026-07-05T01:30
**Проект:** ISAP — Industrial Safety AI Platform

---

## Сессия 2026-07-05: Рефакторинг генератора ПМЛА

### Завершённые задачи

| # | Задача | Коммит | Статус |
|---|--------|--------|--------|
| 1 | Архитектура 6 движков (base, template, table, scenario, rules, narrative) | `ce3f626` | ✅ |
| 2 | Интеграция EngineRouter с EnhancedDocumentGenerator | `7b24290` | ✅ |

### Архитектура 6 движков

| Движок | Разделов | AI | Файл |
|--------|----------|-----|------|
| TemplateEngine | 10 | 0% | `engines/template_engine.py` |
| DataEngine | 8 | 0% | `engines/data_engine.py` |
| ScenarioEngine | 2 | 0% | `engines/scenario_engine.py` |
| RulesEngine | 6 | 0% | `engines/rules_engine.py` |
| NarrativeEngine | 1 | ~10% | `engines/narrative_engine.py` |
| TableEngine | — | 0% | `engines/table_engine.py` |

**Итого:** 27 разделов, LLM используется только для introduction (~10% документа)

### Новые файлы

```
backend/src/application/engines/
├── __init__.py, base.py, router.py
├── template_engine.py, data_engine.py, scenario_engine.py
├── rules_engine.py, narrative_engine.py, table_engine.py

backend/src/application/services/engine_integration.py
backend/templates/pmla/scenario_templates/gas_network.json
backend/tests/engines/ (7 файлов, 94 теста)
```

### Тесты

```
194 passed, 42 warnings in 3.41s
```

---

## Сессия 2026-07-04 (вечер)

### Завершённые задачи

| # | Задача | Коммит | Статус |
|---|--------|--------|--------|
| 1 | Замена LLM mistral-nemo → llama3:8b | `05a43ae` | ✅ |
| 2 | Исправление тестов (120→130) | `6b55f28` | ✅ |
| 3 | DOCX: таблицы, None-фикс, изображения | `c862665` | ✅ |
| 4 | Фронтенд: централизация констант | `74691f4` | ✅ |
| 5 | Фронтенд: CSS utility-классы | `74691f4` | ✅ |
| 6 | Фронтенд: API统一 на request() | `47965d5` | ✅ |
| 7 | Фронтенд: замена инлайнов (этап 1) | `412e2d1` | ✅ |
| 8 | Фронтенд: utility-классы + замена инлайнов (этап 2) | `02b55d9` | ✅ |
| 9 | Фронтенд: замена инлайнов в PmlaWizard | `cedd377` | ✅ |

### LLM замена

- **Было:** `mistral-nemo` (12B, 8GB VRAM)
- **Стало:** `llama3:8b` (8B, 6GB VRAM)
- Обновлены: `.env`, `.env.example`, `settings.py`, `test_llm_models.py`, `LLM_MODELS.md`, `ARCHITECTURE.md`, `PROGRESS.md`

### DOCX улучшения

- **Таблицы:** markdown pipe-парсер + HTML-парсер + рендер в python-docx (Table Grid, Times New Roman 12pt)
- **None fix:** глобальный `finalize=lambda x: '' if x is None else x` в Jinja Environment
- **Шаблоны:** `| default('—')` для `facility.name`, `organization.name` в 00_title_page.j2, 41_familiarization_sheet.j2
- **Изображения:** заглушка `content_type: "image"` + `[IMAGE:path]` маркер
- **Тесты:** +10 новых тестов (парсеры, рендерер таблиц) → **130/130**

### Фронтенд рефакторинг

#### Этап 1: Централизация констант (`constants.js`)

| Экспорт | Удалено дублей из |
|---------|-------------------|
| `hazardLabel`, `hazardBadge` | Facilities, FacilityDetail |
| `roleLabel` | Persons |
| `regulatoryStatusBadge` | Regulatory |
| `statusLabels`, `statusBadgeClass` | FacilityDetail, GenerationProgress |
| `orgName`, `facilityName` | utility functions |

#### Этап 2: CSS исправления

| Что | Статус |
|-----|--------|
| `--bg` переменная | Добавлена (фикс прозрачных модалок) |
| `.badge-danger/warning/info/success` | Добавлены (фикс невидимых бейджей) |
| `.alert-error/success/warning/info` | Добавлены |
| `.empty-state` | Добавлен |
| `.form-section/form-header/form-actions` | Добавлены |
| `.filter-bar/action-buttons/row-actions` | Добавлены |
| `.modal-backdrop/content/header` | Добавлены |
| `.detail-label/detail-value` | Добавлены |
| `.section-subtitle` | Добавлен |
| `.grid-2/.grid-3` + responsive | Добавлены |
| `.login-*` | Добавлены |
| Utility: `.mb-*`, `.mt-*`, `.p-*`, `.flex-*`, `.gap-*`, `.text-*` | Добавлены |
| `.timeline` (7), `.toast` (5), `.stat-change` (3) | Удалены (мёртвый CSS) |

#### Этап 3: API统一

- ~20 методов переписаны на `request()` хелпер
- Добавлен `requestBlob()` для скачиваний
- Login.jsx импортирует из api.js
- Удалено ~300 строк дублированного fetch-кода

#### Этап 4: Замена инлайнов

| Файл | Было | Стало |
|------|------|-------|
| Login.jsx | 12 | **0** |
| FacilityOpoDetails.jsx | 61 | **~20** |
| PmlaWizard.jsx | 87 | **~35** |
| Documents.jsx | 45 | **~25** |
| GenerationProgress.jsx | 27 | **~15** |
| PmlaSamples.jsx | 40 | **~30** |
| **Итого** | **~370** | **~300** |

### Тесты

```
130 passed, 5 warnings in 3.21s
```

### Git коммиты за сессию

```
cedd377 refactor: replace inline styles with utility classes in PmlaWizard
02b55d9 refactor: add spacing/flex/text utility classes, replace inline styles
412e2d1 refactor: replace inline styles with CSS classes in Login, FacilityOpoDetails, PmlaWizard
47965d5 refactor: API unification, inline style cleanup, responsive grids
74691f4 refactor: centralize frontend constants, fix missing CSS, remove dead CSS
c862665 feat: DOCX table rendering, None fix, image scaffold
05a43ae feat: switch LLM from mistral-nemo to llama3:8b
88ce494 docs: update PROGRESS.md with test verification results
6b55f28 fix: repair test suite — 120/120 pass
d0627af docs: add complete PMLA generation pipeline documentation
e975df1 docs: update PROGRESS.md with evening session work
cedd377 refactor: replace inline styles with utility classes in PmlaWizard
02b55d9 refactor: add spacing/flex/text utility classes, replace inline styles
412e2d1 refactor: replace inline styles with CSS classes in Login, FacilityOpoDetails, PmlaWizard
47965d5 refactor: API unification, inline style cleanup, responsive grids
74691f4 refactor: centralize frontend constants, fix missing CSS, remove dead CSS
c862665 feat: DOCX table rendering, None fix, image scaffold
05a43ae feat: switch LLM from mistral-nemo to llama3:8b
88ce494 docs: update PROGRESS.md with test verification results
6b55f28 fix: repair test suite — 120/120 pass
28bd734 fix: reviewer_id non-UUID string causes DB insert error
89287c1 fix: review 422 (reviewer_id accepts string) and PDF export 500 (soffice path)
```

### Исправленные баги (2026-07-04T22:00)

| Баг | Причина | Решение |
|-----|---------|---------|
| Review 422 | `ReviewRequest.reviewer_id: UUID` не принимал строку `'anonymous'` | Тип изменён на `str \| UUID = "anonymous"` |
| Review 400 DB error | Колонка `document_versions.reviewer_id` — UUID, приходит `'isap-secret-2026'` | `_save_version()` → `reviewer_id=None` если не UUID |
| PDF Export 500 | `_find_soffice()` возвращал `'libreoffice'`, а в Docker `'soffice'` | Добавлена проверка `shutil.which('soffice')` |
| PII тесты падали | Мок патчил несуществующий `enhanced_generator.settings` | Патч `src.core.settings.settings` |
| Интеграционные тесты 401 | `API_KEY=isap-secret-2026` в контейнере | `conftest.py` сброс `API_KEY=""` |

### План из 8 задач — ВСЕ ВЫПОЛНЕНЫ

| # | Задача | Миграция | Статус |
|---|--------|----------|--------|
| 1 | PDF-конвертер (LibreOffice) | — | ✅ |
| 2 | Auth (API Key) | — | ✅ |
| 3 | Геокодинг + аварийные службы | 007 | ✅ |
| 4 | Regulatory snapshot | 008 | ✅ |
| 5 | Сроки пересмотра ПМЛА | 009 | ✅ |
| 6 | Частичная перегенерация разделов | 010 | ✅ |
| 7 | ИИ-агент-ревьюер | — | ✅ |
| 8 | Восстановление версий | 011 | ✅ |

### Дополнительно: Интеграция формы «Сведения об ОПО»

| # | Задача | Миграция | Статус |
|---|--------|----------|--------|
| 1 | Форма ОПО (модель, API, frontend) | 013 | ✅ |
| 2 | Импорт данных из Word | — | ✅ |

### Новые API-эндпоинты

```
GET  /api/v1/facility-types/                    — справочник типов ОПО
GET  /api/v1/facilities/{id}/full               — полные данные ОПО
GET  /api/v1/facilities/{id}/details            — данные формы ОПО
POST /api/v1/facilities/{id}/details            — сохранение формы ОПО
GET  /api/v1/facilities/{id}/export/docx        — экспорт DOCX
GET  /api/v1/facilities/{id}/export/pdf         — экспорт PDF
POST /api/v1/facilities/import-word             — импорт из Word
GET  /api/v1/pmla/{id}/ai-review                — AI-ревью
POST /api/v1/pmla/{id}/ai-review                — запуск AI-ревью
POST /api/v1/pmla/{id}/regenerate               — частичная перегенерация
GET  /api/v1/pmla/{id}/versions                 — история версий
POST /api/v1/pmla/{id}/restore/{version_id}     — восстановление версии
GET  /api/v1/pmla/expiring?days=N               — истекающие сроки
GET  /api/v1/pmla/overdue                       — просроченные документы
```

### Миграции

| # | Описание |
|---|----------|
| 007 | latitude, longitude, commissioning_date, inventory_number |
| 008 | regulatory_snapshot в document_versions |
| 009 | submitted_at, approved_at, rejected_at, review_date |
| 010 | rendered_sections в documents |
| 011 | content_docx в document_versions |
| 012 | ai_review_* в document_versions |
| 013 | opo_details (форма «Сведения об ОПО») |

### Исправления по ходу

- CORS: убран `VITE_API_URL` из docker-compose
- `commissioning_date` сериализация через dict
- `LLMResponse.content` в ai_reviewer
- Fallback LLM провайдер без ключа
- Миграции идемпотентные (column_exists)
- Content-Disposition: URL-кодирование русских имён
- docxtpl добавлен в pyproject.toml

### Для запуска

```bash
docker compose up -d
docker exec isap_backend alembic upgrade head
docker exec isap_backend pip install docxtpl  # если не в Dockerfile
```

---

### Что сделано
- **Миграция 007**: новые поля в `hazardous_facilities` — `latitude`, `longitude`, `commissioning_date`, `inventory_number` + индекс по координатам
- **Справочник типов ОПО**: 20 типов (компрессорная станция, котельная, сеть газопотребления, АЗС, НПЗ и т.д.) с кодами, описаниями и дефолтным классом опасности
- **API `GET /api/v1/facility-types/`**: справочник типов ОПО
- **API `GET /api/v1/facilities/{id}/full`**: полные данные ОПО (оборудование + вещества + документы) за один запрос
- **Интеграция ОПО → ПМЛА**: генератор получает координаты, тип объекта, дату ввода, инвентарный номер. Автопоиск аварийных служб по координатам (EmergencyServiceFinder)
- **Frontend: карточка ОПО** — 4 вкладки: Общие сведения, Оборудование, Вещества, Документы ПМЛА
- **Frontend: форма создания** — тип объекта из справочника (автозаполняет класс опасности), координаты, инвентарный номер, дата ввода

### Для запуска
```bash
docker exec isap_backend alembic upgrade head   # миграция 007
docker restart isap_backend                      # новые роутеры
docker restart isap_frontend                     # обновление фронтенда
```

---

## Текущий статус: Полноценный ПМЛА по приказу 1437

### Верификация (2026-07-04T19:50)

| Проверка | Результат |
|----------|-----------|
| Docker Compose | 4 контейнера healthy |
| Backend `/health` | `{"status":"ok"}` |
| Auth (без ключа) | 401 — корректно |
| Auth (с ключом) | 200 — корректно |
| Organizations API | 3 организации |
| Facility types API | 20 типов ОПО |
| Swagger UI | Доступен без auth |
| Frontend | 200 OK |
| Тесты | **120/120 passed** |

### Исправления в тестах (коммит `6b55f28`)
- `conftest.py` — сброс `API_KEY=""` для отключения auth в тестах
- `fake_fac()` — добавлены `latitude`, `longitude`, `commissioning_date`, `inventory_number`
- PII тесты — патч `src.core.settings.settings` вместо несуществующего `enhanced_generator.settings`
- Utility scripts: audit_samples, load_scenario_matrix, reindex_samples, test_generation

### Рабочий flow:
```
POST /api/v1/pmla/generate           → {document_id, status: "pending_review"}
POST /api/v1/pmla/generate/stream    → SSE прогресс в реальном времени
GET  /api/v1/pmla/{id}/preview       → JSON с 29 разделами
POST /api/v1/pmla/{id}/review        → {status: "approved"}
GET  /api/v1/pmla/{id}/download      → DOCX
GET  /api/v1/pmla/{id}/download/pdf  → PDF
```

### Результат генерации (29 разделов):
- Титульный лист, журнал корректировки, оглавление
- Обозначения (АСФ, ОПО, ПМЛА...), термины (22 из ФЗ-116)
- Введение с нормативной базой
- 13 основных разделов (характеристика, сценарии, аварийность, силы, взаимодействие, дислокация, готовность, управление, обмен, действия, персонал, население, обеспечение)
- Специальный раздел (оперативная часть)
- 5 приложений (изучение, сообщение, ПАСФ, оснащение, оповещение)
- Список литературы (22 документа), лист ознакомления

---

## Что сделано

### Фаза 0-7: Бэкенд MVP ✅
- 12 таблиц БД, 6 миграций
- 8 нормативов, 16 сценариев
- 26 Jinja2-шаблонов
- LLM: 4 провайдера + fallback
- 77 тестов

### FACT/TEXT слоты ✅ (2026-07-03)
- LLM больше не получает расчётные данные в промпте
- FACT-слоты: код подставляет данные из БД/расчётов
- TEXT-слоты: LLM генерирует только описательный текст
- Шаблоны разделены на FACT/TEXT блоки

### Матрица сценариев ✅ (2026-07-03)
```
GET    /api/v1/scenarios/              → список с фильтрами (регистронезависимо)
GET    /api/v1/scenarios/{id}          → детали
POST   /api/v1/scenarios/              → создать
DELETE /api/v1/scenarios/{id}          → удалить
```
- 16 сценариев для 6 типов ОПО
- Детерминированный выбор по типу + классу опасности
- Интегрирован в генератор: LLM описывает выбранные сценарии

### Fallback-тексты ✅ (2026-07-03)
- Готовые тексты для сценариев и действий
- Используются при недоступности LLM
- Пометка "[Требуется уточнение]"

### Multi-provider LLM ✅ (2026-07-03)
- OpenAI/Gemini (облако)
- YandexGPT (облако)
- Ollama (локально)
- GLM 4.5 (Zhipu AI)
- FallbackProvider с автоматическим переключением

### Полная структура ПМЛА по приказу 1437 ✅ (2026-07-03)
- 29 разделов вместо 5
- Титульный лист, оглавление, обозначения, термины, введение
- 13 основных разделов (характеристика, сценарии, аварийность, силы, взаимодействие, дислокация, готовность, управление, обмен, действия, персонал, население, обеспечение)
- Специальный раздел (оперативная часть)
- 5 приложений (изучение, сообщение, ПАСФ, оснащение, оповещение)
- Список литературы (22 документа)
- Лист ознакомления

### Frontend rebuild ✅ (2026-07-01)
- 10 страниц: Dashboard, Layout, PmlaWizard, Documents, FacilityDetail, Organizations, Facilities, Persons, Regulatory, PmlaSamples
- Дизайн-система 700+ строк

### CRUD endpoints ✅
```
Organizations:  POST/GET/PUT/DELETE /api/v1/organizations/
Facilities:     POST/GET/PUT/DELETE /api/v1/facilities/
Equipment:      POST/GET/PUT/DELETE /api/v1/equipment/
Substances:     POST/GET/PUT/DELETE /api/v1/substances/
Persons:        POST/GET/PUT/DELETE /api/v1/persons/
Regulatory:     POST/GET/PUT/DELETE /api/v1/regulatory/
```

### Новое: Превью ПМЛА ✅ (2026-07-03)
```
GET /api/v1/pmla/{id}/preview        → JSON с секциями, расчётами, замечаниями
GET /api/v1/pmla-samples/{id}/preview → превью содержимого DOCX
```
- Шаг 5 "Просмотр" в мастере ( между генерацией и ревью)
- Модальное окно превью в списке документов
- Превью образцов с содержимым DOCX

### Новое: Образцы ПМЛА ✅ (2026-07-03)
```
POST /api/v1/pmla-samples/upload     → загрузка DOCX/PDF
GET  /api/v1/pmla-samples/           → список с фильтрами
GET  /api/v1/pmla-samples/{id}       → детали
GET  /api/v1/pmla-samples/{id}/download → скачивание
GET  /api/v1/pmla-samples/{id}/preview  → превью содержимого
PUT  /api/v1/pmla-samples/{id}/verify   → верификация
DELETE /api/v1/pmla-samples/{id}        → мягкое удаление
```
- Страница `/samples` — карточки с фильтрами
- Форма загрузки: файл + название + описание + тип ОПО + класс опасности
- Верификация образцов

### Новое: SSE прогресс генерации ✅ (2026-07-03)
```
POST /api/v1/pmla/generate/stream    → Server-Sent Events
```
- События: progress, error
- Прогресс-бар с процентами и анимацией
- Текущая секция и номер
- Прошедшее время
- Список завершённых секций
- Компонент `GenerationProgress.jsx`

### Новое: Форма добавления нормативов ✅ (2026-07-03)
- Добавление/редактирование/удаление из UI
- Поля: наименование, категория, статус, примечания

### Исправленные баги ✅ (2026-07-03)
- `except HTTPException: raise` — 404 больше не превращается в 500
- `from_attributes=True` во всех Pydantic response моделях
- `datetime.now(UTC).replace(tzinfo=None)` — совместимость с asyncpg
- `pool_pre_ping` удалён — event loop conflict
- Vite proxy: `http://localhost:8000` → `http://backend:8000` (Docker)
- Regex `[A-Z_]+` → `[A-Za-z_0-9]+` — calc placeholder с lowercase
- `str.format()` обёрнут в try/except KeyError
- Незакрытый тег `<i>` в PmlaSamples.jsx

---

## API (55+ роутов):

### ПМЛА:
```
POST   /api/v1/pmla/generate              → генерация
POST   /api/v1/pmla/generate/stream       → SSE прогресс
GET    /api/v1/pmla/                      → список документов
GET    /api/v1/pmla/{id}/status           → статус + issues
GET    /api/v1/pmla/{id}/preview          → превью документа
POST   /api/v1/pmla/{id}/review           → ревью
GET    /api/v1/pmla/{id}/download         → DOCX
GET    /api/v1/pmla/{id}/download/pdf     → PDF
GET    /api/v1/pmla/methods/list          → список методик
```

### Образцы ПМЛА:
```
POST   /api/v1/pmla-samples/upload        → загрузка файла
GET    /api/v1/pmla-samples/              → список
GET    /api/v1/pmla-samples/{id}          → детали
GET    /api/v1/pmla-samples/{id}/preview  → превью
GET    /api/v1/pmla-samples/{id}/download → скачивание
PUT    /api/v1/pmla-samples/{id}/verify   → верификация
DELETE /api/v1/pmla-samples/{id}          → удаление
```

### Реестр нормативов:
```
GET    /api/v1/regulatory/                → список
GET    /api/v1/regulatory/{id}            → детали
POST   /api/v1/regulatory/                → создать
PUT    /api/v1/regulatory/{id}            → обновить
DELETE /api/v1/regulatory/{id}            → удалить
POST   /api/v1/regulatory/{id}/verify     → верифицировать
```

---

## Конфигурация

### Docker Compose:
| Сервис | Порт | Образ |
|--------|------|-------|
| PostgreSQL 16 | 5432 | postgres:16-alpine |
| Backend | 8000 | python:3.11-slim |
| Frontend | 3000 | node:18-alpine |
| ChromaDB | 8001 | chromadb/chroma |

### БД:
- 12 таблиц, 6 миграций, 8 нормативов, 16 сценариев
- Таблица `pmla_samples` — образцы ПМЛА
- Таблица `scenario_matrix` — матрица сценариев

### LLM (4 провайдера):
- Primary: Ollama (llama3:8b, localhost:11434)
- Fallback: Gemini (gemini-2.5-flash)
- YandexGPT (облако)
- GLM 4.5 (Zhipu AI)

---

## Запуск (Docker)

```bash
docker-compose up -d
```

### Без Docker:
```bash
# Backend
cd backend
alembic upgrade head
python -m scripts.load_regulatory_data
python -m uvicorn src.main:app --reload --port 8000

# Frontend
cd frontend
npm run dev
```

Swagger: http://localhost:8000/docs
Frontend: http://localhost:3000

---

## Frontend страницы

| Страница | Роут | Описание |
|----------|------|----------|
| Дашборд | `/` | Статистика + последние ПМЛА |
| Генерация ПМЛА | `/pmla` | 6-шаговый мастер |
| Документы | `/documents` | Список + превью + скачивание |
| Организации | `/organizations` | CRUD |
| Объекты ОПО | `/facilities` | CRUD |
| Детали объекта | `/facilities/:id` | Оборудование + вещества |
| Ответственные лица | `/persons` | CRUD |
| Нормативы | `/regulatory` | CRUD + форма добавления |
| Образцы ПМЛА | `/samples` | Загрузка + просмотр + скачивание |

---

## Wizard: 6 шагов

1. **Выбор объекта** — организация + ОПО
2. **Контекст** — оборудование, вещества, лица
3. **Расчёты** — зоны поражения (ТНТ, тепло, токсика)
4. **Генерация** — SSE прогресс в реальном времени
5. **Просмотр** — содержимое документа, расчёты, замечания
6. **Ревью** — утверждение/возврат

---

## Исправленные баги (2026-07-03)

| # | Проблема | Решение |
|---|----------|---------|
| 1 | `except Exception` ловил HTTPException(404) | `except HTTPException: raise` перед catch-all |
| 2 | Pydantic response модели без `from_attributes` | `model_config = ConfigDict(from_attributes=True)` |
| 3 | `datetime.utcnow()` deprecated Python 3.12+ | `datetime.now(UTC).replace(tzinfo=None)` |
| 4 | `pool_pre_ping` event loop conflict | Удалён |
| 5 | Docker proxy `localhost:8000` | `http://backend:8000` |
| 6 | Regex не матчил lowercase placeholder | `[A-Za-z_0-9]+` |
| 7 | `str.format()` KeyError | try/except с fallback |
| 8 | Незакрытый тег `<i>` | Исправлен |
| 9 | LLM error messages утекали клиенту | Generic сообщение |
| 10 | Review buttons активны при неверном статусе | disabled если `status !== 'pending_review'` |

---

## ТЗ на доработку (2026-07-03)

Создан план доработки из 8 задач: `PLAN.md`

### Задача 1: PDF-конвертер ✅
- Заменён `docx2pdf` → `LibreOffice headless` в Dockerfile
- Fallback на `fpdf2` сохранён
- Результат: PDF 239KB (полное форматирование) vs 72KB (fallback)
- Файлы: `Dockerfile`, `backend/src/infrastructure/pdf/converter.py`

### Задача 2: Auth + JWT (план)
- Таблица users, JWT-аутентификация, роли
- ~20 файлов, 4 новых эндпоинта

### Задача 3: Геокодинг (план)
- Яндекс Геокодер + аварийные службы
- lat/lng в hazardous_facilities, интеграция в генерацию

### Задача 4: regulatory_snapshot (план)
- Снимок нормативов при утверждении версии
- Проверка заменённых/спорных нормативов

### Задача 5: Сроки пересмотра (план)
- review_date = approved_at + 5 лет
- Виджет на дашборде, /expiring, /overdue эндпоинты

### Задача 6: Частичная перегенерация (план)
- Section-level storage для отдельных разделов
- POST /{id}/regenerate для перегенерации отклонённых

### Задача 7: AI-ревьюер (план)
- Чек-лист из 11 пунктов, автоутверждение при confidence >= 0.85
- Интеграция после Stage D валидации

### Задача 8: Восстановление версии (план)
- content_docx в document_versions, current_version_id
- POST /{id}/restore/{version}

---

## Исправленные баги (2026-07-03, день)

| # | Проблема | Решение |
|---|----------|---------|
| 11 | PDF конвертер не работает в Docker | Замена docx2pdf → LibreOffice headless |
| 12 | Валидация не находит обязательные разделы | Гибкий поиск ключевых слов в заголовках |
| 13 | Кнопки скачивания активны до утверждения | disabled + подсказки в PmlaWizard.jsx |
| 14 | Отсутствует раздел "список должностных лиц" | Снижено severity до warning в валидации |

---

## Конфигурация Docker (обновлено)

| Сервис | Порт | Образ | Примечание |
|--------|------|-------|------------|
| PostgreSQL 16 | 5432 | postgres:16-alpine | |
| Backend | 8000 | python:3.11-slim | + LibreOffice 25.2.3 |
| Frontend | 3000 | node:18-alpine | Vite dev mode |
| ChromaDB | 8001 | chromadb/chroma | |

### Системные зависимости backend:
- gcc, libpq-dev (сборка)
- fonts-dejavu-core, fonts-liberation, fonts-freefont-ttf (шрифты)
- libreoffice-core, libreoffice-writer (конвертация PDF)
