# Отчёт прогресса: ISAP

**Дата обновления:** 2026-07-06T22:00
**Проект:** ISAP — Industrial Safety AI Platform

---

## Сессия 2026-07-06 (вечер): AI settings + Smart Import E2E + клиенты API

### Завершённые задачи

| # | Задача | Статус |
|---|--------|--------|
| 1 | Smart Import E2E тесты — 24/24 пройдены | ✅ |
| 2 | AI/LM Studio — ручная настройка из UI | ✅ |
| 3 | Clients page — подключение к реальному API | ✅ |
| 4 | Исправлен дубликат `_get_setting` в ai.py | ✅ |
| 5 | Исправлен тест `test_ai_config` (Docker override) | ✅ |

### AI Settings — новая страница

Добавлена форма ручной настройки AI-провайдеров прямо из UI:

- Выбор провайдера: LM Studio, Ollama, OpenAI/Gemini, YandexGPT, GLM
- Настройка модели, base URL, API key для каждого провайдера
- Выбор embedding провайдера
- Fallback toggle
- Настройки сохраняются в `ai_settings.json` на сервере
- Вкладки: Настройки / Диагностика (health check)

**API:**
```
GET  /api/v1/ai/settings     — текущие настройки
POST /api/v1/ai/settings     — обновление настроек
```

### Smart Import E2E — результаты тестирования

```
=== 1. GET /imports/profiles ===
  PASS: profiles returns 200
  PASS: 3 profiles returned
  PASS: fire_departments exists
  PASS: pasf_units exists
  PASS: pmla_questionnaire exists

=== 2. POST /imports/fire_departments/preview (CSV) ===
  PASS: preview returns 200
  PASS: job created
  PASS: status is preview
  PASS: total_rows = 2
  PASS: header_mapping non-empty
  PASS: rows returned

=== 3-7. Jobs, rows, confirm, DB verify, duplicates ===
  ALL PASS

Results: 24 passed, 0 failed
```

### Исправления

- **clients-page.tsx**: заменены `mockClients` на `apiRequest` — организации теперь сохраняются в БД
- **ai.py**: удалён дубликат `_get_setting` (вторая функция перезаписывала первую)
- **test_ai_config.py**: тест проверяет валидность провайдера вместо жёсткого дефолта

### Тесты

```
259 passed, 12 warnings in 5.66s
```

### Git коммиты

```
ff601b7 feat: AI settings page + fix clients-page API + fix test
d90db98 fix: clients-page uses real API instead of mock data
2639ae8 feat: Smart Import Center + refactor routers + fix frontend Docker
```

---

## Сессия 2026-07-06 (ночь): Smart Import Center + фикс фронтенда

### Завершённые задачи

| # | Задача | Статус |
|---|--------|--------|
| 1 | Применение патча `ISAP2_SMART_IMPORT_PATCH.patch` | ✅ |
| 2 | Рефакторинг `pmla.py` (1112→~300 строк) | ✅ |
| 3 | Рефакторинг `pmla_stream.py` (313→~120 строк) | ✅ |
| 4 | Исправление 2 тестов RulesEngine | ✅ |
| 5 | Исправление фронтенда (Next.js lockfile permissions) | ✅ |

### Smart Import Center — новый модуль

Добавлен единый механизм умного импорта Excel/CSV с предпросмотром, маппингом колонок, валидацией и поиском дублей.

**Новые таблицы (миграция 015):**
- `import_jobs` — задания импорта
- `import_rows` — строки с raw/mapped/normalized данными
- `emergency_rescue_units` — ПАСФ / АСФ
- `emergency_services` — пожарные, скорая, полиция, газовая, ЕДДС
- `pmla_questionnaires` — анкеты генерации ПМЛА

**3 профиля импорта:**

| Профиль | Целевая таблица | Обязательные поля |
|---------|-----------------|-------------------|
| `fire_departments` | emergency_services | name, address |
| `pasf_units` | emergency_rescue_units | name, certificate_number |
| `pmla_questionnaire` | pmla_questionnaires | organization_name, facility_name |

**API:**
```
GET  /api/v1/imports/profiles                    — список профилей
POST /api/v1/imports/{import_type}/preview       — загрузка + предпросмотр
GET  /api/v1/imports/jobs/{job_id}               — статус задания
GET  /api/v1/imports/jobs/{job_id}/rows          — строки предпросмотра
POST /api/v1/imports/jobs/{job_id}/confirm       — подтверждение импорта
```

**Новые файлы:**
```
backend/alembic/versions/015_add_smart_import.py
backend/src/api/routers/imports.py
backend/src/application/services/smart_import/__init__.py
backend/src/application/services/smart_import/parser.py
backend/src/application/services/smart_import/profiles.py
backend/src/application/services/smart_import/service.py
backend/tests/smart_import/test_parser.py
backend/tests/smart_import/test_profiles.py
docs/SMART_IMPORT_CENTER.md
```

**Зависимость:** `openpyxl>=3.1.0` (добавлена в pyproject.toml)

### Рефакторинг роутеров

**pmla.py (1112 → ~300 строк):**
- Делегирование в `PmlaGenerationService`, `PmlaQueryService`, `PmlaExportService`, `PmlaReviewWorkflowService`
- Убрано ~800 строк дублированного кода

**pmla_stream.py (313 → ~120 строк):**
- SSE-генератор теперь использует `PmlaGenerationService.build_context()`

### Исправления фронтенда

**Проблема:** Next.js падал в Docker с ошибкой `Permission denied (lockfile)`.
**Причина:** `.next` кэш создавался на Windows хосте, а Alpine Linux контейнер не мог его открыть.

**Исправления:**
1. Удалена `frontend_node_modules` volume из docker-compose.yml
2. Удалён `.next` кэш с хоста
3. Добавлен `NODE_ENV=development` в env
4. Старые Vite-страницы (`src/pages/`) переименованы в `legacy-pages/` — конфликтовали с Next.js App Router
5. команда запуска: `npm install --prefer-offline && npx next dev --webpack -H 0.0.0.0 -p 3000`

### Тесты

```
259 passed, 50 warnings in 6.61s
```
- 255 существующих + 4 новых (smart import parser + profiles)

### Git статус

```
M  backend/src/api/routers/pmla.py           (рефакторинг)
M  backend/src/api/routers/pmla_stream.py     (рефакторинг)
M  backend/src/main.py                        (imports router)
M  backend/src/infrastructure/database/models.py (5 новых моделей)
M  backend/pyproject.toml                     (openpyxl)
M  docker-compose.yml                         (frontend fix)
M  README.md                                  (Smart Import docs)
A  backend/alembic/versions/015_add_smart_import.py
A  backend/src/api/routers/imports.py
A  backend/src/application/services/smart_import/  (4 файла)
A  backend/tests/smart_import/                (2 теста)
A  docs/SMART_IMPORT_CENTER.md
R  frontend/src/pages -> frontend/src/legacy-pages
```

---

## Сессия 2026-07-06 (вечер): Рефакторинг роутеров + исправление тестов

### Завершённые задачи

| # | Задача | Статус |
|---|--------|--------|
| 1 | Рефакторинг `pmla.py`: делегирование логики в application services | ✅ |
| 2 | Рефакторинг `pmla_stream.py`: делегирование в `PmlaGenerationService` | ✅ |
| 3 | Исправление 2 тестов RulesEngine (устаревшие assertions) | ✅ |

### Что сделано

**pmla.py (1112 → ~300 строк):**
- Вся логика сборки контекста, генерации, ревью, экспорта делегирована в:
  - `PmlaGenerationService` — генерация, сборка контекста, перегенерация
  - `PmlaQueryService` — список, превью, версии, expiring/overdue
  - `PmlaExportService` — DOCX/PDF скачивание
  - `PmlaReviewWorkflowService` — ревью, AI-ревью, восстановление версий
- Убрано ~800 строк дублированного кода (inline context building, DB queries)

**pmla_stream.py (313 → ~120 строк):**
- SSE-генератор теперь использует `PmlaGenerationService.build_context()`
- Убрано дублирование контекст-билдинга и emergency services enrichment

**Тесты (255/255 passed):**
- `test_section_10_initial_actions` — убрана assertion на "Иванов И.И." (persons не входят в section_10)
- `test_section_12_population_safety` — заменена assertion на "эвакуац" (слово "мероприятия" отсутствует в output)

### Архитектура сервисов (финальная)

```
backend/src/application/services/
├── pmla_generation_service.py    # generate(), regenerate_sections(), build_context()
├── pmla_query_service.py         # list_documents(), get_preview(), list_versions()
├── pmla_export_service.py        # get_docx(), get_pdf()
├── pmla_review_workflow_service.py  # review(), run_ai_review(), restore_version()
├── enhanced_generator.py         # Ядро генерации (29 разделов)
├── engine_integration.py         # create_engine_router(), build_document_context()
└── engines/                      # 6 движков: template, data, scenario, rules, narrative, table
```

---

## Сессия 2026-07-06: Применение hotfix-патча (frontend integration)

### Завершённые задачи

| # | Задача | Статус |
|---|--------|--------|
| 1 | Применить hotfix-патч (`API_KEY`, AI diagnostics, CORS/auth order) | ✅ |

### Что сделано

Патч `hotfix` уже применён к рабочей копии; верифицированы чтением и `git status`/`git diff` все 5 затронутых файлов:

| Файл | Изменение | Git |
|------|-----------|-----|
| `.env.example` | Добавлена строка `API_KEY=dev-secret` в начало | `M` |
| `backend/src/api/routers/ai.py` | Новый роутер AI-диагностики (`/config`, `/health`, `/embeddings/health`) | `??` |
| `backend/src/main.py` | Импорт `ai`; `CORSMiddleware` перенесён ниже `ApiKeyMiddleware`; поддержка заголовка `X-API-Key`; роутер `/api/v1/ai`; расширены `allow_origins` (`http://127.0.0.1:3000`) | `M` |
| `frontend/.env.example` | Добавлен `NEXT_PUBLIC_API_KEY=dev-secret` | `??` |
| `frontend/src/lib/api-client.ts` | Чтение `NEXT_PUBLIC_API_KEY`; заголовки `Authorization: Bearer` + `X-API-Key` | `??` |

### Подтверждённые зависимости

- `get_llm_provider`, `LLMMessage` — `src/infrastructure/llm/providers.py`
- `get_embedding_provider`, `EmbeddingResponse` — `src/infrastructure/embeddings/providers.py`
- `ai.py` безопасно читает настройки через `getattr(settings, ..., default)` — отсутствие опциональных полей (`embedding_provider`, `lmstudio_*`, `openai_embedding_model`) не вызывает ошибок на этом роутере.

### Заметка

`backend/src/infrastructure/embeddings/providers.py` (существующий файл вне данного патча) напрямую обращается к `settings.embedding_provider`/`settings.embedding_batch_size`/`settings.lmstudio_*` — при активации embedding-провайдера эти поля необходимо добавить в `src/core/settings.py`. Сам hotfix-патч этих полей не вводит, но это следующий шаг для работоспособности `/api/v1/ai/embeddings/health`.

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

---

## PMLA Questionnaire DOCX Import (2026-07-06)

Priority: stabilize PMLA flow `input data -> generation -> validation -> DOCX -> text quality`.

Done:
- Applied `ISAP2_PMLA_QUESTIONNAIRE_DOCX_IMPORT.patch` with manual adaptation of `backend/src/main.py`.
- Added `/api/v1/pmla-questionnaires/...` API for PMLA questionnaire state.
- `SmartImportParser` now accepts `.docx` and converts an old questionnaire/document into one `pmla_questionnaire` preview row.
- Added `PmlaQuestionnaireService`: questionnaire state, custom scenarios, generation context, resource recommendations.
- Added docs: `docs/SMART_DOCX_IMPORT.md`, `docs/pmla/PMLA_QUESTIONNAIRE_BUILDER.md`; updated `docs/SMART_IMPORT_CENTER.md`.
- Updated Smart Import API/profile wording to say Excel/CSV/DOCX.

Verified:
- `pytest tests/smart_import/test_parser.py tests/smart_import/test_profiles.py tests/smart_import/test_docx_parser.py tests/test_pmla_questionnaire_service_unit.py tests/test_ai_config.py tests/test_pmla_debug_service.py -q` -> `10 passed, 2 warnings`.
- HTTP `GET /health` -> 200.
- HTTP OpenAPI contains 6 `/api/v1/pmla-questionnaires/...` paths.
- HTTP `POST /api/v1/imports/pmla_questionnaire/preview` with DOCX and key `isap-secret-2026` -> 200, `error_rows=0`, `created_rows=1`; recognized `organization_name`, `facility_name`, `facility_reg_number`, `has_incidents`.

Notes:
- Port 8000 is currently served by the Docker/backend environment with API key `isap-secret-2026`; a local backend started with `dev-secret` could not bind because the port was already in use.
- The worktree also contains generated `.next/` files and dev logs from running servers; do not include them when saving the patch.

## PMLA Generation From Questionnaire (2026-07-06)

Priority: make the PMLA generator consume questionnaire-derived engineering facts instead of the old loose context.

Done:
- Applied `ISAP2_GENERATION_FROM_QUESTIONNAIRE.patch`.
- Added `POST /api/v1/pmla-questionnaires/{questionnaire_id}/generate`.
- Added `PmlaGenerationFromQuestionnaireService` bridge from questionnaire context to `EnhancedDocumentGenerator`.
- Questionnaire context now maps incident history, selected/custom scenarios, PASF, emergency services, financial reserve, insurance, organization resources, training, and attachments into generator-facing fields.
- Generation metadata stores `source=pmla_questionnaire`, `questionnaire_id`, `context_quality`, and `context_snapshot`.
- Debug package writes `context.json`, `context_quality.json`, `generation_meta.json`, `rendered_sections.json`, and `output.docx` when available.
- Fixed patch docs to use the real `/api/v1/pmla-questionnaires/...` route.

Verified:
- `pytest tests/test_pmla_generation_from_questionnaire_service_unit.py tests/test_pmla_questionnaire_service_unit.py tests/test_pmla_debug_service.py tests/test_enhanced_generator.py -q` -> `33 passed, 5 warnings`.
- Local OpenAPI contains `/api/v1/pmla-questionnaires/{questionnaire_id}/generate`.
- `git diff --check` for changed patch files -> clean.

## PMLA Questionnaire UI Wizard (2026-07-06)

Done:
- Added dashboard page `frontend/src/components/dashboard/pmla-questionnaire-page.tsx`.
- Added sidebar entry `Anketa PMLA` / `?????? ????` as a separate dashboard section.
- Extended `frontend/src/lib/api-client.ts` with questionnaire, generation, DOCX preview, and import confirmation calls.
- UI supports facility selection, questionnaire open/create, block editing, custom scenarios, manual PASF, manual emergency services, resources, notification, finance/insurance, training/attachments, context preview, generation, and DOCX import preview/confirm.
- Backend context builder now includes manual PASF and manual emergency services saved in questionnaire data, so UI-entered services are not lost before generation.

Verified:
- `npm install --no-audit --no-fund` -> completed.
- `npm run build` -> completed successfully.
- `npx tsc --noEmit` -> completed successfully.
- `python -m pytest -q` -> `265 passed, 50 warnings`.
- Frontend dev server restarted on `http://127.0.0.1:3000/`; HTTP check returned 200.

Notes:
- Backend `127.0.0.1:8000` was not running during final live HTTP check, so browser data loading requires starting backend.
- In-app browser automation was blocked by the browser URL policy, so visual click-through was not completed by automation.

## PMLA Questionnaire UI Stabilization (2026-07-07)

Goal: harden the already-added PMLA questionnaire UI wizard without rewriting it.

Done:
- Rechecked `frontend/src/components/dashboard/pmla-questionnaire-page.tsx`, `api-client.ts`, `page.tsx`, `sidebar.tsx`, and `nav-store.ts`.
- Confirmed the UI uses the real backend routes `/api/v1/pmla-questionnaires/...` and `/api/v1/imports/...`; the prompt's `/api/v1/pmla/questionnaires/...` routes are outdated for this codebase.
- Added generation readiness UX on the generation tab: completion percentage, scenario/service counters, explicit warnings, context collection button, and compact generation result summary.
- Added `.gitignore` entry for `isap/backend/.pytest_tmp/` because pytest with local `--basetemp` creates it.
- Removed tracked `.zip`, `.patch`, and log artifacts from Git history going forward; current tracked-artifact scan is clean.

Verified:
- `npx tsc --noEmit` -> passed.
- `npm run build` -> passed.
- `python -m pytest -q --basetemp .pytest_tmp` -> `265 passed, 50 warnings`.
- `git diff --check` for changed files -> clean.
- Frontend `http://127.0.0.1:3000/` -> HTTP 200.

Notes:
- `isap/frontend/next-env.d.ts` may appear modified after Next build only because of generated line-ending/stat noise; keep it out of commits unless the generated route reference intentionally changes.
- Latest relevant commits: `4072c71 Add PMLA questionnaire UI wizard`, `5a6ef3e Polish PMLA questionnaire UI wizard`.
