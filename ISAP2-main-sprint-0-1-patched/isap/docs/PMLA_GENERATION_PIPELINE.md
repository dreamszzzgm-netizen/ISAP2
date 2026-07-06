# Пайплайн генерации ПМЛА — полное описание

**Дата:** 2026-07-04
**Проект:** ISAP — Industrial Safety AI Platform

---

## Содержание

1. [Архитектура](#1-архитектура)
2. [Загрузка и индексация образцов](#2-загрузка-и-индексация-образцов)
3. [Генерация документа (основной пайплайн)](#3-генерация-документа)
4. [RAG-пайплайн](#4-rag-пайплайн)
5. [Расчёты](#5-расчёты)
6. [Конвертация PDF](#6-конвертация-pdf)
7. [Скачивание и экспорт](#7-скачивание-и-экспорт)
8. [Карта базы данных](#8-карта-базы-данных)
9. [Список файлов](#9-список-файлов)

---

## 1. Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (React 18)                                        │
│  PmlaWizard.jsx → GenerationProgress.jsx → api.js          │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP / SSE
┌──────────────────────▼──────────────────────────────────────┐
│  API Layer (FastAPI routers)                                │
│  pmla.py, pmla_stream.py, pmla_samples.py                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  Application Layer (services)                               │
│  EnhancedDocumentGenerator, DocumentValidator,              │
│  AIReviewer, SampleIntegrationService, CalculationRegistry  │
└──────────┬───────────┬───────────┬─────────────────────────┘
           │           │           │
┌──────────▼──┐ ┌──────▼─────┐ ┌──▼──────────────┐
│  LLM (Ollama│ │  RAG       │ │  Database        │
│  /Gemini)   │ │  ChromaDB  │ │  PostgreSQL 16   │
└─────────────┘ └────────────┘ └──────────────────┘
```

| Уровень | Расположение |
|---------|-------------|
| Frontend | `frontend/src/` |
| API | `backend/src/api/routers/` |
| Business Logic | `backend/src/application/services/` |
| Infrastructure | `backend/src/infrastructure/` |
| Templates | `backend/templates/pmla/` |
| Bootstrap | `backend/src/main.py` |

---

## 2. Загрузка и индексация образцов

### 2.1 Загрузка файла

```
PmlaSamples.jsx (UploadForm)
  → pmlaSamplesApi.upload(formData)              [api.js:192]
  → POST /api/v1/pmla-samples/upload             [pmla_samples.py:37]
  → PmlaSampleRepository.create()                [pmla_sample_repo.py]
  → Запись файла: backend/uploads/pmla_samples/{timestamp}_{name}.docx
  → Таблица: pmla_samples (title, description, file_path, facility_type, hazard_class, is_verified=0)
```

### 2.2 Верификация → Индексация в ChromaDB

```
PmlaSamples.jsx (кнопка "Верифицировать")
  → pmlaSamplesApi.verify(id)                    [api.js:198]
  → PUT /api/v1/pmla-samples/{id}/verify         [pmla_samples.py:182]
  → SampleIntegrationService.on_sample_verified()
    → SampleIndexer.index_sample()               [sample_indexer.py]
      → DocumentLoader.load(file_path)           [pipeline.py]
      → Chunker(chunk_size=100).chunk(docs)      [pipeline.py]
      → Embedder.embed_chunks(chunks)            [pipeline.py]
      → VectorStore("isap_samples").add()        [pipeline.py]
  → ChromaDB коллекция: isap_samples
```

### 2.3 Структурная индексация (продвинутая)

```
StructuralSampleIndexer.index_sample()            [structural_pipeline.py:102]
  → parse_pmla_docx(file_path)                   [structural_pipeline.py:35]
    → SectionDetector.detect(paragraphs)          [parsers/section_detector.py]
    → StructuralChunker.chunk(sections)           [parsers/chunker.py]
  → Embedder.embed_chunks(chunks)
  → VectorStore("isap_samples").add()
  → Метаданные чанков: sample_id, section_id, facility_type, hazard_class
```

### 2.4 Загрузка корпуса знаний

```
CorpusLoader.load_all()                          [corpus_loader.py:46]
  → Источник 1: regulatory_documents → chunks → isap_knowledge
  → Источник 2: documents (утверждённые ПМЛА) → rendered_sections → isap_knowledge
  → Источник 3: data/corpus/*.txt, *.pdf, *.docx → isap_knowledge
  → Источник 4: pmla_content.txt (эталон) → isap_knowledge
```

---

## 3. Генерация документа

### 3.1 Фронтенд: Мастер (6 шагов)

**Файл:** `frontend/src/pages/PmlaWizard.jsx`

| Шаг | Название | Что происходит |
|-----|----------|----------------|
| 1 | Выбор объекта | Загрузка организаций, ОПО, оборудования, веществ, лиц |
| 2 | Контекст | Отображение загруженных данных |
| 3 | Расчёты | Информационные карточки 3 методик |
| 4 | Генерация | SSE-подключение к `/generate/stream`, прогресс-бар |
| 5 | Просмотр | `pmlaApi.preview(id)` — содержимое DOCX как JSON |
| 6 | Ревью | Утверждение/возврат через `pmlaApi.review()` |

**Файл:** `frontend/src/pages/GenerationProgress.jsx`
- Подключение к SSE: `POST /api/v1/pmla/generate/stream?facility_id=...`
- События: `progress` (процент, секция), `error`, `complete`
- При завершении: `onComplete({document_id, status})`

### 3.2 API: Сборка контекста

**Файл:** `backend/src/api/routers/pmla.py`

```
generate_pmla(facility_id)                       [pmla.py:51]
  → SELECT hazardous_facilities WHERE id=facility_id
  → SELECT organizations WHERE id=facility.organization_id
  → SELECT equipment WHERE hazardous_facility_id=facility_id
  → SELECT hazardous_substances WHERE hazardous_facility_id=facility_id
  → SELECT responsible_persons WHERE organization_id=...
  → EmergencyServiceFinder.find_nearest(lat, lng)  [если есть координаты]
  → INSERT INTO documents (status='processing')
  → EnhancedDocumentGenerator.generate(document_id, context)
```

### 3.3 Генератор: Основной пайплайн

**Файл:** `backend/src/application/services/enhanced_generator.py`

#### Этап A: Загрузка структуры

```
_load_structure("pmla")                          [line 728]
  → Читает templates/pmla/structure.json
  → Возвращает 29 секций с content_type (data/llm), template, rag_query
```

#### Этап B: Расчёты

```
_run_calculations(context)                       [line 427]
  → Для каждого вещества из context["substances"]:
    → Если есть explosion_energy_mj:
      → ExplosionZoneCalculation.calculate()     [calculations/explosion_zone.py]
      → method_id = "tnt_equivalent_v1"
    → Если есть combustion_energy_mj_kg:
      → ThermalRadiationCalculation.calculate()  [calculations/thermal_radiation.py]
      → method_id = "thermal_radiation_v1"
    → Если есть mac_mg_m3:
      → ToxicExposureCalculation.calculate()     [calculations/toxic_exposure.py]
      → method_id = "toxic_dispersion_v1"
  → Результат: [{method_id, substance, input_params, results, validation_status}]
```

#### Этап B2: Выбор сценариев

```
_select_scenarios(context)                       [line 102]
  → SELECT FROM scenario_matrix
    WHERE facility_type = context.facility.facility_type
    AND hazard_class = context.facility.hazard_class
  → Детерминированный выбор (без LLM)
  → Результат: [{id, name, factor_type, calculation_method, probability}]
```

#### Этап B3: Обогащение контекста

```
_enrich_context(context, scenarios, calculations) [line 133]
  → Добавляет: year, approver, personnel, scenarios,
    calculation_results, facility_coords, material_reserve
```

#### Этап A2: Контекст из образцов

```
StructuralSampleIntegrationService.build_sample_context(section_id, title, facility_type, hazard_class)
  → StructuralSampleRetriever.retrieve_by_section()  [structural_pipeline.py:186]
    → ChromaDB query: isap_samples collection
    → Фильтр: section_id + facility_type + hazard_class
  → _find_best_sample() → SELECT pmla_samples WHERE facility_type + hazard_class
  → _extract_section_from_sample() → parse_pmla_docx()
  → Результат: {rag_context, few_shot_example}
```

#### Этап C: Генерация текста (29 секций)

Для каждой секции из `structure.json`:

**Если `content_type == "data"`:**
```
_render_template(jinja_env, template_name, context)
  → Jinja2 рендерит шаблон напрямую из данных контекста
```

**Если `content_type == "llm"`:**
```
1. _get_rag_context(section, context)             [line 539]
   → _build_rag_query(rag_query_template, context)
   → Embedder.embed_query(query)
   → VectorStore("isap_knowledge").search(embedding, top_k=5)
   → Результат: текст из нормативных документов

2. StructuralSampleIntegrationService.build_sample_context()
   → Few-shot примеры + RAG-контекст из образцов

3. _generate_section_llm(...)                     [line 574]
   → PII-роутинг: pii=true → local_llm, иначе → external_llm
   → strip_pii(context) — очистка персональных данных
   → build_section_prompt() — сборка промпта:
     * SYSTEM_PROMPT (эксперт по ПБ)
     * Данные объекта, веществ, оборудования
     * RAG-контекст из нормативов
     * Few-shot примеры из образцов
     * Ограничения (только текст, без чисел)
   → llm.complete(messages) — вызов LLM
   → Постобработка: удаление **маркёртов**
   → Fallback: get_fallback_text() или _fallback_section_content()

4. _render_template(jinja_env, template_name, render_ctx)
   → Jinja2 рендерит шаблон с llm_content + calc_placeholders
```

#### Этап D: Валидация

```
DocumentValidator.validate(rendered_sections, context, calc_results) [validation.py]
  → check_mandatory_sections — все ли обязательные секции есть
  → check_numbers_match — совпадают ли числа в тексте и расчётах
  → check_contacts — есть ли контактные данные
  → check_regulatory_references — проверка ссылок на НПА
  → Результат: ValidationResult(passed, issues)
```

#### Этап D2: AI-ревью (опционально)

```
AIReviewer(llm).review(rendered_sections, context) [ai_reviewer.py]
  → 11 пунктов чек-листа через LLM:
    1. Сценарии соответствуют типу ОПО
    2. Причины и зоны указаны
    3. Зоны совпадают с расчётами
    4. Мероприятия привязаны к сценариям
    5. СИЗ соответствуют классу
    6. Системы защиты учтены
    7. Алгоритм действий логичен
    8. Ответственные лица присутствуют
    9. Порядок оповещения указан
    10. Аварийные службы совпадают
    11. Разделы не противоречат
  → Результат: AIReviewResult(confidence, decision, items, summary)
  → confidence >= 0.85 → auto_approve
  → confidence < 0.85 → escalate_to_human
```

#### Этап E: Сборка DOCX

```
_build_docx(title, rendered_sections, metadata)   [line 904]
  → DocxDocument() — создание документа
  → _setup_document_defaults(doc):
    * A4 (21×29.7 см)
    * Поля: верх/низ 2см, лево 3см, право 1.5см
    * Шрифт: Times New Roman 12pt
    * Отступ первой строки: 1.25см
    * Выравнивание: по ширине
  → _add_heading(doc, title, level=0) — заголовок документа
  → Для каждой секции:
    * _add_heading(doc, section_title, level=1)
    * _render_content_to_docx(doc, content):
      - Парсит markdown-таблицы → _add_table()
      - Парсит HTML-таблицы → _add_table()
      - Конвертирует ## заголовки → _add_heading()
      - Остальное → _add_body_paragraph() (с **bold** парсингом)
  → Добавление расчётов и замечаний валидации
  → buffer.getvalue() → bytes
```

#### Этап F: Сохранение

```
→ UPDATE documents SET content_docx, rendered_sections, status, generation_meta
→ INSERT calculation_results (для каждого метода)
→ INSERT document_versions (снимок версии с AI-ревью)
→ Версия: DocumentVersionModel с content_docx, ai_review_*, regulatory_snapshot
→ Результат: GeneratedDocument(document_id, docx_bytes, version_number, status)
```

---

## 4. RAG-пайплайн

### 4.1 Компоненты

| Компонент | Файл | Назначение |
|-----------|------|-----------|
| DocumentLoader | `rag/pipeline.py` | Загрузка PDF/TXT/DOCX → list[Document] |
| Chunker | `rag/pipeline.py` | Разбиение на фиксированные чанки с перекрытием |
| Embedder | `rag/pipeline.py` | OpenAI text-embedding-3-small или Ollama nomic-embed-text |
| VectorStore | `rag/pipeline.py` | Обёртка над ChromaDB |
| Retriever | `rag/pipeline.py` | Высокоуровневый интерфейс запросов |
| SectionDetector | `rag/parsers/section_detector.py` | 29 regex-паттернов для определения разделов |
| StructuralChunker | `rag/parsers/chunker.py` | Чанкинг с учётом границ разделов |

### 4.2 Коллекции ChromaDB

| Коллекция | Назначение | Наполняется |
|-----------|-----------|-------------|
| `isap_knowledge` | Нормативные документы, утверждённые ПМЛА, корпус | `CorpusLoader.load_all()` |
| `isap_samples` | Верифицированные образцы ПМЛА | `SampleIndexer` / `StructuralSampleIndexer` |

### 4.3 Запросы

```
RAG-запрос для LLM-секции:
  → _build_rag_query("аварийные ситуации на {facility_type}", context)
  → Embedder.embed_query(query)
  → VectorStore("isap_knowledge").search(embedding, top_k=5)
  → Валидные чанки → контекст для LLM

Запрос к образцам:
  → StructuralSampleRetriever.retrieve_by_section(section_id, facility_type, hazard_class)
  → VectorStore("isap_samples").search(embedding, filters={section_id, facility_type})
  → Лучший пример → few-shot контекст
```

---

## 5. Расчёты

| Метод | Файл | Входные данные | Результат |
|-------|------|---------------|-----------|
| `tnt_equivalent_v1` | `calculations/explosion_zone.py` | quantity_kg, explosion_energy_mj, physical_state | Радиус зоны взрыва (м) |
| `thermal_radiation_v1` | `calculations/thermal_radiation.py` | quantity_kg, combustion_energy_mj_kg | Радиус теплового поражения (м) |
| `toxic_dispersion_v1` | `calculations/toxic_exposure.py` | quantity_kg, mac_mg_m3, lc50_mg_m3, physical_state | Радиус токсического облака (м) |

**Валидация:** `CalculationValidator` проверяет диапазоны входных данных перед расчётом.

**Регистрация:** Модули автоматически регистрируются в `CalculationRegistry` при импорте.

---

## 6. Конвертация PDF

**Файл:** `backend/src/infrastructure/pdf/converter.py`

```
docx_bytes_to_pdf(docx_bytes)
  → Tier 1: _convert_via_libreoffice(docx_bytes)
    → tempfile: input.docx
    → soffice --headless --convert-to pdf --outdir tmpdir
    → Читает result.pdf
    → Таймаут: 120 секунд
  → Tier 2 (fallback): _convert_via_fpdf(docx_bytes)
    → python-docx: извлечение текста и таблиц
    → fpdf2: создание PDF с DejaVu шрифтом
    → Потеря форматирования (таблицы как текст)
```

Вызывается из: `pmla.py` → `download_pmla_pdf()` endpoint.

---

## 7. Скачивание и экспорт

### 7.1 Стандартный экспорт ПМЛА

| Endpoint | Файл | Возврат |
|----------|------|---------|
| `GET /{id}/download` | `pmla.py:308` | `doc.content_docx` как StreamingResponse |
| `GET /{id}/download/pdf` | `pmla.py:335` | PDF через `docx_bytes_to_pdf()` |
| `GET /{id}/preview` | `pmla.py:369` | Парсинг DOCX → JSON с секциями |

**Ограничение:** Скачивание доступно только при `status == "approved"`.

### 7.2 Экспорт формы ОПО (отдельный пайплайн)

| Функция | Файл | Назначение |
|---------|------|-----------|
| `generate_opo_docx(data)` | `export/brand_engine.py` | Рендер формы ОПО в DOCX через docxtpl |
| `generate_opo_pdf(data)` | `export/brand_engine.py` | DOCX → PDF через LibreOffice |

---

## 8. Карта базы данных

| Таблица | Модель | R/W в пайплайне |
|---------|--------|-----------------|
| `organizations` | `OrganizationModel` | READ (контекст) |
| `hazardous_facilities` | `HazardousFacilityModel` | READ (контекст, координаты) |
| `equipment` | `EquipmentModel` | READ (контекст) |
| `hazardous_substances` | `HazardousSubstanceModel` | READ (контекст, расчёты) |
| `responsible_persons` | `ResponsiblePersonModel` | READ (контекст) |
| `documents` | `DocumentModel` | WRITE (новый документ), UPDATE (контент, статус) |
| `document_versions` | `DocumentVersionModel` | WRITE (снимок версии, AI-ревью) |
| `calculation_results` | `CalculationResultModel` | WRITE (результаты расчётов) |
| `pmla_samples` | `PmlaSampleModel` | WRITE (загрузка), READ (поиск лучшего) |
| `scenario_matrix` | `ScenarioMatrixModel` | READ (выбор сценариев) |
| `regulatory_documents` | `RegulatoryDocumentModel` | READ (валидация, корпус) |

---

## 9. Список файлов

### Frontend (6 файлов)

| Файл | Назначение |
|------|-----------|
| `frontend/src/pages/PmlaWizard.jsx` | 6-шаговый мастер генерации |
| `frontend/src/pages/PmlaSamples.jsx` | Управление образцами |
| `frontend/src/pages/GenerationProgress.jsx` | SSE-прогресс генерации |
| `frontend/src/api.js` | API-клиенты |
| `frontend/src/components/WordImportButton.jsx` | Импорт ОПО из Word |
| `frontend/src/constants.js` | Статусы и справочники |

### API-роутеры (3 ключевых файла)

| Файл | Маршруты |
|------|---------|
| `api/routers/pmla.py` | generate, status, review, download, preview, regenerate, restore, ai-review, versions |
| `api/routers/pmla_stream.py` | SSE-генерация |
| `api/routers/pmla_samples.py` | upload, list, preview, download, verify, delete |

### Сервисы приложения (11 файлов)

| Файл | Класс/Функция |
|------|--------------|
| `services/enhanced_generator.py` | `EnhancedDocumentGenerator` — главный оркестратор |
| `services/validation.py` | `DocumentValidator` — 4 проверки |
| `services/ai_reviewer.py` | `AIReviewer` — 11-пунктный чек-лист |
| `services/review_service.py` | `ReviewService` — workflow утверждения |
| `services/prompts.py` | `build_section_prompt()`, `SYSTEM_PROMPT` |
| `services/types.py` | `Issue`, `ValidationResult`, `GeneratedDocument`, `AIReviewResult` |
| `services/fallback_texts.py` | `get_fallback_text()` для офлайн-режима |
| `services/sample_integration.py` | `SampleIntegrationService` (простой) |
| `services/structural_sample_integration.py` | `StructuralSampleIntegrationService` (продвинутый) |
| `services/word_import_service.py` | `WordImportService` (парсинг ОПО) |
| `services/calculations/` | 7 файлов: registry, types, base, validation, 3 модуля расчётов |

### Инфраструктура (14 файлов)

| Файл | Класс/Функция |
|------|--------------|
| `infrastructure/database/models.py` | 11 SQLAlchemy моделей |
| `infrastructure/database/engine.py` | `async_session_factory` |
| `infrastructure/rag/pipeline.py` | `DocumentLoader`, `Chunker`, `Embedder`, `VectorStore`, `Retriever` |
| `infrastructure/rag/corpus_loader.py` | `CorpusLoader` — массовая загрузка знаний |
| `infrastructure/rag/sample_indexer.py` | `SampleIndexer` (простой чанкинг) |
| `infrastructure/rag/sample_retriever.py` | `SampleRetriever` |
| `infrastructure/rag/structural_pipeline.py` | `parse_pmla_docx()`, `StructuralSampleIndexer`, `StructuralSampleRetriever` |
| `infrastructure/rag/parsers/section_detector.py` | `SectionDetector` — 29 regex-паттернов |
| `infrastructure/rag/parsers/chunker.py` | `StructuralChunker` |
| `infrastructure/rag/parsers/models.py` | `DetectedSection`, `DetectionReport` |
| `infrastructure/llm/providers.py` | 5 LLM-провайдеров + фабрика |
| `infrastructure/pdf/converter.py` | `docx_bytes_to_pdf()` |
| `infrastructure/export/brand_engine.py` | `generate_opo_docx()`, `generate_opo_pdf()` |
| `infrastructure/repositories/document_repo.py` | `DocumentRepository` |

### Шаблоны (28 файлов)

| Файл | Назначение |
|------|-----------|
| `templates/pmla/structure.json` | Определения 29 секций |
| `templates/pmla/sections/00_title_page.j2` | Титульный лист |
| `templates/pmla/sections/00_correction_log.j2` | Журнал корректировки |
| `templates/pmla/sections/00_toc.j2` | Оглавление |
| `templates/pmla/sections/00_abbreviations.j2` | Обозначения |
| `templates/pmla/sections/00_terms.j2` | Термины |
| `templates/pmla/sections/00_introduction.j2` | Введение (LLM) |
| `templates/pmla/sections/01_characteristics.j2` | Характеристика ОПО |
| `templates/pmla/sections/02_scenarios.j2` | Сценарии аварий (LLM) |
| `templates/pmla/sections/03_accident_history.j2` | Аварийность |
| `templates/pmla/sections/04_forces.j2` | Силы и средства |
| `templates/pmla/sections/05_interaction.j2` | Взаимодействие (LLM) |
| `templates/pmla/sections/06_composition.j2` | Состав и дислокация |
| `templates/pmla/sections/07_readiness.j2` | Готовность (LLM) |
| `templates/pmla/sections/08_management.j2` | Управление и связь |
| `templates/pmla/sections/09_information_exchange.j2` | Обмен информацией (LLM) |
| `templates/pmla/sections/10_initial_actions.j2` | Начальные действия (LLM) |
| `templates/pmla/sections/11_personnel_actions.j2` | Действия персонала (LLM) |
| `templates/pmla/sections/12_population_safety.j2` | Безопасность населения (LLM) |
| `templates/pmla/sections/13_material_support.j2` | Материальное обеспечение |
| `templates/pmla/sections/20_special_section.j2` | Специальный раздел (LLM) |
| `templates/pmla/sections/30_appendix_1.j2` — `34_appendix_5.j2` | 5 приложений |
| `templates/pmla/sections/40_bibliography.j2` | Список литературы |
| `templates/pmla/sections/41_familiarization_sheet.j2` | Лист ознакомления |

---

## Полная схема потока данных

```
Пользователь выбирает объект в PmlaWizard.jsx
  │
  ▼
POST /api/v1/pmla/generate { facility_id }
  │
  ▼
pmla.py: generate_pmla()
  ├── SELECT hazardous_facilities, organizations, equipment,
  │   hazardous_substances, responsible_persons
  ├── Сборка контекста dict
  ├── EmergencyServiceFinder (геокодирование)
  ├── INSERT INTO documents (status=processing)
  │
  ▼
EnhancedDocumentGenerator.generate(document_id, context)
  │
  ├── _load_structure("pmla") → structure.json (29 секций)
  │
  ├── _run_calculations(context)
  │     └── Для каждого вещества: Explosion / Thermal / Toxic
  │         Returns: [{method_id, input_params, results}]
  │
  ├── _select_scenarios(context)
  │     └── SELECT FROM scenario_matrix WHERE facility_type + hazard_class
  │         Returns: [{id, name, factor_type, probability}]
  │
  ├── _enrich_context(context, scenarios, calculations)
  │     └── Добавляет year, approver, personnel, etc.
  │
  ├── ДЛЯ КАЖДОЙ ИЗ 29 СЕКЦИЙ:
  │     │
  │     ├── content_type == "data":
  │     │     └── _render_template(jinja2, template.j2, context)
  │     │
  │     ├── content_type == "llm":
  │     │     ├── _get_rag_context() → ChromaDB "isap_knowledge"
  │     │     ├── StructuralSampleIntegrationService.build_sample_context()
  │     │     │     └── ChromaDB "isap_samples" + лучший образец
  │     │     ├── _generate_section_llm()
  │     │     │     ├── strip_pii(context)
  │     │     │     ├── build_section_prompt()
  │     │     │     ├── llm.complete(messages) → текст
  │     │     │     └── fallback: get_fallback_text()
  │     │     └── _render_template() с llm_content + calc_placeholders
  │
  ├── DocumentValidator.validate()
  │     └── 4 проверки: секции, числа, контакты, НПА
  │
  ├── AIReviewer.review() [если включено]
  │     └── 11-пунктный чек-лист через LLM
  │
  ├── _build_docx(title, sections, metadata)
  │     └── python-docx: A4, Times New Roman, таблицы, bold
  │         Returns: bytes (DOCX)
  │
  ├── UPDATE documents (content_docx, status, meta)
  ├── INSERT calculation_results
  ├── INSERT document_versions (снимок + AI-ревью)
  │
  ▼
GeneratedDocument(document_id, docx_bytes, version_number, status)
  │
  ▼
Статус: "pending_review" (или "auto_validation_failed")
  │
  ▼
Пользователь просматривает (Шаг 5) и утверждает (Шаг 6)
  │
  ├── Утверждение: POST /{id}/review {decision: "approved"}
  │     └── UPDATE documents SET status="approved"
  │
  ├── Скачивание DOCX: GET /{id}/download
  │     └── StreamingResponse(doc.content_docx)
  │
  └── Скачивание PDF: GET /{id}/download/pdf
        └── docx_bytes_to_pdf() → StreamingResponse
```
