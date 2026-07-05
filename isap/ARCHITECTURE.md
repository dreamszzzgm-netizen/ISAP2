# ISAP — Полное описание работы системы

## Содержание

1. [Обзор системы](#1-обзор-системы)
2. [Инфраструктура](#2-инфраструктура)
3. [Работа пользователя](#3-работа-пользователя)
4. [Справочники (CRUD)](#4-справочники-crud)
5. [Генерация ПМЛА — полный пайплайн](#5-генерация-пмЛА-полный-пайплайн)
6. [RAG — поисковое усиление генерации](#6-rag-поисковое-усиление-генерации)
7. [LLM — генерация текста](#7-llm-генерация-текста)
8. [Шаблоны и структура документа](#8-шаблоны-и-структура-документа)
9. [Образцы ПМЛА — few-shot + RAG](#9-образцы-пмла-few-shot--rag)
10. [Автоматическая валидация](#10-автоматическая-валидация)
11. [Ревью и утверждение](#11-ревью-и-утверждение)
12. [Экспорт документа](#12-экспорт-документа)
13. [Архитектура кода](#13-архитектура-кода)

---

## 1. Обзор системы

**ISAP (Industrial Safety AI Platform)** — платформа автоматизации разработки Планов мероприятий по локализации и ликвидации последствий аварий (ПМЛА) для опасных производственных объектов (ОПО).

**Что делает система:**
- Собирает данные об объекте (организация, оборудование, вещества, ответственные лица)
- Автоматически генерирует 29-раздельный документ ПМЛА по приказу Ростехнадзора №1437
- Использует LLM (языковую модель) для генерации текстовых разделов
- Использует RAG (поиск по векторной базе) для усиления генерации нормативными фрагментами
- Использует образцы реальных ПМЛА как примеры стиля (few-shot)
- Выполняет расчёты (взрыв, тепловое излучение, токсическое воздействие)
- Автоматически валидирует результат
- Конвертирует в DOCX и PDF

**Стек:**
- Backend: Python 3.11, FastAPI, SQLAlchemy async, PostgreSQL 16, Alembic
- Frontend: React 18, React Router 7, кастомный CSS (без UI-библиотек)
- LLM: Ollama (llama3:8b) / Gemini API / YandexGPT
- RAG: ChromaDB (векторная БД), собственный пайплайн без фреймворков
- Docker: 4 контейнера (db, backend, frontend, chromadb)

---

## 2. Инфраструктура

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend   │────▶│   Backend   │────▶│ PostgreSQL  │
│  React/Vite  │     │   FastAPI   │     │     DB      │
│  :3000       │     │   :8000     │     │   :5432     │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │   ChromaDB  │
                    │  :8001      │
                    └─────────────┘
                           │
                    ┌──────┴──────┐
                    │   Ollama    │
                    │  (LLM)     │
                    │  на хосте   │
                    └─────────────┘
```

**Контейнеры Docker:**
- `isap_db` — PostgreSQL 16 (порт 5432)
- `isap_backend` — FastAPI (порт 8000), подключается к БД, ChromaDB, Ollama
- `isap_frontend` — Node.js 18 + Vite dev server (порт 3000), проксирует `/api` на backend
- `isap_chromadb` — ChromaDB (порт 8001), хранит векторные представления нормативов и образцов

**Базы данных:**
- PostgreSQL — 13 таблиц: organizations, hazardous_facilities, equipment, hazardous_substances, responsible_persons, documents, document_versions, regulatory_documents, calculation_results, pmla_samples, scenario_matrix, (+ users при auth)
- ChromaDB — 2 коллекции: `isap_knowledge` (нормативная база), `isap_samples` (образцы ПМЛА)

---

## 3. Работа пользователя

### 3.1. Авторизация

Единый API-ключ. Хранится в `localStorage` браузера. Без ключа — редирект на страницу `/login`.

```
[Логин] → ввод ключа → проверка запросом к /api/v1/organizations/
  → OK → сохранение в localStorage → редирект на /
  → 401 → ошибка "Неверный ключ доступа"
```

### 3.2. Навигация

Боковая панель с тремя группами:
- **Основное:** Дашборд, Генерация ПМЛА, Документы
- **Справочники:** Организации, Объекты ОПО, Ответственные лица
- **Система:** Нормативы, Образцы ПМЛА

### 3.3. Рабочий процесс (типичный)

```
1. Создать организацию (ИНН, название, адрес)
2. Создать объект ОПО (привязка к организации, тип, класс опасности)
3. Добавить оборудование и опасные вещества
4. Добавить ответственных лиц
5. (Опционально) Загрузить образец ПМЛА, верифицировать
6. Запустить генерацию ПМЛА
7. Проверить результат, при необходимости — перегенерировать
8. Утвердить документ
9. Скачать DOCX или PDF
```

---

## 4. Справочники (CRUD)

Все справочники работают по единому паттерну:

```
Frontend (api.js) → REST API (router) → Repository → SQLAlchemy → PostgreSQL
```

### Организации
- `POST /api/v1/organizations/` — создание
- `GET /api/v1/organizations/` — список (с пагинацией skip/limit)
- `GET /api/v1/organizations/{id}` — получение
- `PUT /api/v1/organizations/{id}` — обновление
- `DELETE /api/v1/organizations/{id}` — удаление

### Объекты ОПО
- Аналогичный CRUD
- Поля: `name`, `reg_number`, `hazard_class` (I-IV), `facility_type`, `address`, `organization_id`

### Оборудование
- Привязано к объекту ОПО (`hazardous_facility_id`)
- Поля: `name`, `equipment_type`, `serial_number`, `manufacturer`, `specifications` (JSONB)

### Опасные вещества
- Привязаны к объекту ОПО
- Поля: `name`, `cas_number`, `quantity_kg`, `threshold_quantity_kg`, `hazard_properties` (JSONB)

### Ответственные лица
- Привязаны к организации
- Поля: `full_name`, `position`, `role`, `phone`, `email`

### Нормативные документы
- Собственный справочник с версионированием
- Поля: `title`, `category`, `status`, `replacement_id` (самоссылка), `last_verified_at`

---

## 5. Генерация ПМЛА — полный пайплайн

Это центральный процесс системы. Вызывается через `POST /api/v1/pmla/generate`.

### Этап A: Сборка контекста

```
1. Получаем facility_id из запроса
2. Запрашиваем из БД:
   - Organization (ИНН, название, адрес, контакты)
   - HazardousFacility (тип, класс опасности, адрес)
   - Equipment[] (оборудование объекта)
   - HazardousSubstance[] (опасные вещества)
   - ResponsiblePerson[] (ответственные лица организации)
3. Собираем context dict:
   {
     "organization": {name, inn, address, phone, email},
     "facility": {name, facility_type, hazard_class, reg_number, address},
     "equipment": [{name, equipment_type, serial_number}, ...],
     "substances": [{name, quantity_kg, cas_number, hazard_properties}, ...],
     "responsible_persons": [{full_name, position, role, phone}, ...]
   }
```

### Этап B: Расчётный блок

```
Для каждого вещества с расчётными параметрами в hazard_properties:
  - explosion_energy_mj → расчёт зоны взрыва (TNT-эквивалент)
  - combustion_energy_mj_kg → расчёт теплового излучения
  - mac_mg_m3 → расчёт токсического воздействия

Результаты: [{method_id, substance, input_params, results, validation_status}]
```

### Этап B2: Выбор сценариев из матрицы

```
1. Берём facility_type и hazard_class из контекста
2. Запрос к таблице scenario_matrix:
   SELECT * FROM scenario_matrix
   WHERE lower(facility_type) = lower(?)
     AND lower(hazard_class) = lower(?)
     AND is_active = 1
3. Результат — список сценариев:
   [{id: "СГ-1", name: "Выброс газа", factor_type: "Токсическое облако",
     calculation_method: "toxic_dispersion_v1", probability: "высокая"}, ...]
```

### Этап A2: Контекст из образцов

```
Для каждого LLM-раздела:
1. Ищем верифицированный образец с совпадающим facility_type + hazard_class
2. RAG-поиск: query = название раздела → ChromaDB (isap_samples) → топ-5 фрагментов
3. Few-shot: извлекаем текст нужного раздела из DOCX образца
4. Передаём в промпт:
   - "--- ФРАГМЕНТЫ ИЗ ОБРАЗЦОВ ПМЛА ---" (RAG)
   - "--- ПРИМЕР ИЗ РЕАЛЬНОГО ПМЛА ---" (few-shot)
```

### Этап C: Генерация текста

Для каждого из 29 разделов:

```
Если content_type == "data":
  → Рендеринг Jinja2 шаблона с данными из контекста (без LLM)

Если content_type == "llm":
  1. RAG-поиск по нормативной базе (ChromaDB: isap_knowledge)
  2. Контекст из образцов (RAG + few-shot)
  3. Построение промпта для LLM:
     - System prompt: "Ты эксперт по промышленной безопасности..."
     - User prompt: название раздела + данные объекта + RAG-фрагменты + образцы
  4. Отправка в LLM (Ollama/Gemini/YandexGPT)
  5. Постобработка: удаление Markdown-маркеров
  6. Fallback: если LLM не ответил → текст из fallback_texts.py
  7. Рендеринг Jinja2 шаблона с llm_content + FACT-данными
```

### Этап D: Автоматическая валидация

```
1. Проверка обязательных разделов (все 29 заполнены)
2. Проверка числовых данных (совпадение с расчётами)
3. Проверка контактов (телефоны заполнены)
4. Проверка нормативных ссылок (актуальность в реестре)

Результат: {passed: bool, issues: [{section, reason, severity}]}
  - passed=true → status="pending_review"
  - passed=false → status="auto_validation_failed"
```

### Этап E: Сборка DOCX

```
1. python-docx: создаёт Document()
2. Заголовок документа (Heading 0)
3. Метаданные (версия, дата, статус)
4. Для каждого раздела:
   - Heading 1: название раздела
   - Параграфы: текст, разбитый по строкам
5. Расчётные данные (если есть)
6. Замечания валидации
7. Сохранение в bytes → content_docx в БД
```

### Этап F: Сохранение

```
1. DocumentModel: content_docx, status, generation_meta
2. CalculationResultModel: результаты расчётов
3. DocumentModel: document_versions (версия 1, 2, ...)
```

---

## 6. RAG — поисковое усиление генерации

**RAG (Retrieval-Augmented Generation)** — поиск релевантных фрагментов из векторной базы для усиления генерации LLM.

### Архитектура RAG

```
[Документы] → DocumentLoader → [Document]
                                    ↓
                              Chunker → [Chunk]
                                    ↓
                              Embedder → [(Chunk, Vector)]
                                    ↓
                              VectorStore → ChromaDB
                                    ↓
[Запрос LLM] → Embedder → Query Vector → VectorStore.search()
                                              ↓
                                      [Релевантные Chunk]
                                              ↓
                                      Добавляются в промпт LLM
```

### Компоненты

**DocumentLoader** (`pipeline.py`):
- Поддержка: PDF (PyMuPDF), DOCX (python-docx), TXT
- PDF: постраничный разбор
- DOCX: все параграфы → один текстовый документ

**Chunker** (`pipeline.py`):
- Разбивка на чанки по `chunk_size` слов с перекрытием `overlap`
- Нормативы: `chunk_size=500`, `overlap=50`
- Образцы: `chunk_size=100`, `overlap=20`

**Embedder** (`pipeline.py`):
- Создание векторных представлений (эмбеддингов)
- Ollama: модель `nomic-embed-text` (768 измерений)
- OpenAI: модель `text-embedding-3-small`
- Батчевая обработка по 100 текстов

**VectorStore** (`pipeline.py`):
- Обёртка над ChromaDB
- Две коллекции: `isap_knowledge` (нормативы), `isap_samples` (образцы)
- Косинусное расстояние для поиска
- Метаданные: `source`, `chunk_index`, `doc_type`, `facility_type`, `hazard_class`

**Retriever** (`pipeline.py`):
- Высокоуровневый интерфейс: текстовый запрос → релевантные чанки
- По умолчанию: `top_k=5`

### Два источника RAG

1. **Нормативная база** (`isap_knowledge`):
   - Загружается через `POST /api/v1/corpus/upload`
   - ФЗ, приказы, ГОСТ, СП
   - Индексируется при загрузке

2. **Образцы ПМЛА** (`isap_samples`):
   - Загружаются через `POST /api/v1/pmla-samples/upload`
   - Верифицированные образцы индексируются автоматически
   - Фильтрация по `facility_type` + `hazard_class`

### Как RAG работает при генерации

```python
# В enhanced_generator.py, для каждого LLM-раздела:
rag_context = await self._get_rag_context(section, context)

# _get_rag_context():
rag_query = section["rag_query"]  # Например: "сценарии аварий сеть газопотребления"
rag_chunks = await self._retriever.retrieve(rag_query)
return "\n\n".join(c.content for c in rag_chunks)

# Результат добавляется в промпт:
"""
--- ФРАГМЕНТЫ ИЗ НОРМАТИВНОЙ БАЗЫ ---
{rag_context}
"""
```

---

## 7. LLM — генерация текста

### Провайдеры

Стратегия паттерн с фолбэком:

```
LLMProvider (ABC)
  ├── OpenAIProvider    — Gemini API / OpenAI API
  ├── OllamaProvider    — локальная модель
  ├── YandexGPTProvider — Яндекс GPT
  ├── GLMProvider       — ChatGLM
  └── FallbackProvider  — автоматический переключатель
```

**Конфигурация:**
- `LLM_PROVIDER=ollama` → основной провайдер
- `LLM_FALLBACK_ENABLED=true` → автоматический фолбэк
- `OLLAMA_MODEL=llama3:8b` → модель для генерации
- `OPENAI_MODEL=gemini-2.5-flash` → модель для Gemini API

### Промпт для LLM

**System prompt** (общий для всех разделов):
```
Ты — эксперт по промышленной безопасности с 10-летним стажем.
Твоя задача — разработать раздел ПМЛА в строгом соответствии с
Постановлением Правительства РФ №1437 и ФЗ №116-ФЗ.

КРИТИЧЕСКИЕ ТРЕБОВАНИЯ:
1. Пиши ТОЛЬКО на русском языке в официально-деловом стиле
2. Используй формулировки из НПА
3. НЕ используй канцелярские шаблоны — пиши конкретно для данного ОПО
4. Ссылайся на конкретное оборудование и вещества
5. НЕ указывай конкретные числа — они подставляются системой
```

**User prompt** (для каждого раздела):
```
Раздел: {section_title}

--- ДАННЫЕ ОБ ОПО ---
Объект: {name}
Тип: {facility_type}
Класс опасности: {hazard_class}
Адрес: {address}

Опасные вещества:
- Нефть сырая: 50000 кг
- Метан: 2000 кг

Оборудование:
- Насос НКУ-100/50
- Резервуар РВС-5000

--- ФРАГМЕНТЫ ИЗ НОРМАТИВНОЙ БАЗЫ ---
{rag_context}

--- ФРАГМЕНТЫ ИЗ ОБРАЗЦОВ ПМЛА ---
{sample_rag_context}

--- ПРИМЕР ИЗ РЕАЛЬНОГО ПМЛА ---
{few_shot_example}

--- ЗАДАНИЕ ---
Напиши текст раздела «{section_title}» для данного ОПО.
```

### FACT/TEXT разделение

Ключевой принцип: **LLM получает ТОЛЬКО текстовые данные**. Числовые данные подставляются кодом.

- `content_type = "data"` — шаблон рендерится целиком из данных (без LLM)
- `content_type = "llm"` — LLM генерирует текст, затем подставляются FACT-данные
- `slot_type = "fact"` — код подставляет числа
- `slot_type = "text"` — LLM генерирует текст
- `slot_type = "mixed"` — комбинация

### Fallback

Если LLM недоступен или не отвечает:
1. Попытка взять текст из `fallback_texts.py` (предустановленные тексты)
2. Если нет → генерация из входных данных: "Объект: {name}, Тип: {type}..."
3. Пометка: `[Раздел «...» требует доработки экспертом по ПБ.]`

---

## 8. Шаблоны и структура документа

### structure.json

Определяет 29 разделов документа:

```
sections:
  - title_page           (data)  Титульный лист
  - correction_log       (data)  Журнал корректировки
  - toc                  (data)  Содержание
  - abbreviations        (data)  Перечень обозначений
  - terms                (data)  Термины и определения
  - introduction         (llm)   Введение
  - section_1            (data)  Характеристика ОПО
  - section_2            (llm)   Сценарии аварий
  - section_3            (data)  Характеристика аварийности
  - section_4            (data)  Силы и средства
  - section_5            (llm)   Взаимодействие сил
  - section_6            (data)  Состав и дислокация
  - section_7            (llm)   Готовность сил
  - section_8            (data)  Управление, связь, оповещение
  - section_9            (llm)   Обмен информацией
  - section_10           (llm)   Первоочередные действия
  - section_11           (llm)   Действия персонала
  - section_12           (llm)   Безопасность населения
  - section_13           (data)  Материально-техническое обеспечение
  - special_section      (llm)   Специальный раздел (оперативная часть)
  - appendix_1           (data)  Порядок изучения ПМЛА
  - appendix_2           (data)  Форма оперативного сообщения
  - appendix_3           (data)  Состав ПАСФ
  - appendix_4           (data)  Оснащение ПАСФ
  - appendix_5           (data)  Схема оповещения
  - bibliography         (data)  Список литературы
  - familiarization_sheet(data)  Лист ознакомления
```

**Итого:** 14 разделов `data` (без LLM) + 13 разделов `llm` (генерируются LLM) + 2 служебных.

### Jinja2 шаблоны

Каждый раздел — отдельный `.j2` файл в `templates/pmla/sections/`:

```
00_title_page.j2       — титул с подписями
00_correction_log.j2   — пустая таблица
00_toc.j2              — оглавление
00_abbreviations.j2    — список сокращений
00_terms.j2            — 20+ терминов из ФЗ-116
00_introduction.j2     — введение (LLM)
01_characteristics.j2  — таблицы 1-3: объект, вещества, оборудование
02_scenarios.j2        — матрица сценариев (LLM)
03_accident_history.j2 — статистика аварий
04_forces.j2           — расчёт сил и средств
05_interaction.j2      — взаимодействие (LLM)
06_composition.j2      — состав сил
07_readiness.j2        — готовность (LLM)
08_management.j2       — управление и связь
09_information_exchange.j2 — обмен (LLM)
10_initial_actions.j2  — первоочередные действия (LLM)
11_personnel_actions.j2— действия персонала (LLM)
12_population_safety.j2— безопасность населения (LLM)
13_material_support.j2 — материальное обеспечение
20_special_section.j2  — спецраздел (LLM)
30_appendix_1.j2       — обучение
31_appendix_2.j2       — форма сообщения
32_appendix_3.j2       — состав ПАСФ
33_appendix_4.j2       — оснащение
34_appendix_5.j2       — схема оповещения
40_bibliography.j2     — нормативы
41_familiarization_sheet.j2 — лист ознакомления
```

### Переменные в шаблонах

Все переменные используют `| default('—')` для безопасной подстановки:

```jinja2
{# TEXT-блок (LLM) #}
{{ llm_content | default('...не сформировано.') }}

{# FACT-блок (код) #}
{{ facility.name | default('—') }}
{{ organization.inn | default('—') }}

{# Таблица #}
{% for s in substances %}
| {{ s.name }} | {{ s.quantity_kg | default('—') }} кг |
{% endfor %}
```

---

## 9. Образцы ПМЛА — few-shot + RAG

### Загрузка

```
Пользователь → фронтенд (форма) → POST /api/v1/pmla-samples/upload
  → Файл сохраняется на диск (backend/uploads/pmla_samples/)
  → Запись в таблицу pmla_samples (is_verified=0)
```

### Верификация + индексация

```
PUT /api/v1/pmla-samples/{id}/verify?is_verified=true
  → UPDATE pmla_samples SET is_verified=1
  → SampleIntegrationService.on_sample_verified()
    → SampleIndexer.index_sample()
      → DocumentLoader.load(file_path)     — парсинг DOCX/PDF
      → Chunker.chunk(docs)                — разбивка на чанки (100 слов)
      → Embedder.embed_chunks(chunks)      — создание эмбеддингов (nomic-embed-text)
      → VectorStore.add(embedded)          — сохранение в ChromaDB (isap_samples)
```

### Использование при генерации

```
Для каждого LLM-раздела:
  SampleIntegrationService.build_sample_context(
    section_title, facility_type, hazard_class
  )
    → SampleRetriever.retrieve_sample_chunks()  — RAG-поиск (top-5)
    → SampleRetriever.get_sample_section()      — few-shot извлечение
    → Возврат: {rag_context, few_shot_example}

  → Добавляется в промпт LLM:
    "--- ФРАГМЕНТЫ ИЗ ОБРАЗЦОВ ПМЛА ---"
    "{rag_context}"
    "--- ПРИМЕР ИЗ РЕАЛЬНОГО ПМЛА ---"
    "{few_shot_example}"
    "Используй этот пример как ориентир по стилю."
```

### Удаление

```
PUT /api/v1/pmla-samples/{id}/verify?is_verified=false
  → UPDATE pmla_samples SET is_verified=0
  → SampleIntegrationService.on_sample_unverified()
    → SampleIndexer.remove_sample()     — удаление из ChromaDB
```

---

## 10. Автоматическая валидация

`DocumentValidator` проверяет документ после генерации:

### 1. Обязательные разделы
```python
mandatory = [
    ("характеристика", ["характеристика"]),
    ("сценарии", ["сценари"]),
    ("введение", ["введение"]),
    ("силы и средства", ["силы", "средства"]),
    # ... ещё 15+ проверок
]
# Проверяется: хотя бы одно ключевое слово найдено в содержимом раздела
```

### 2. Числовые данные
```
Проверка: числа в тексте совпадают с результатами расчётов
- Количество вещества в тексте = quantity_kg из БД
- Радиусы поражения = calculation_results
```

### 3. Контакты
```
Проверка: у ответственных лиц заполнены телефоны
- Если phone пустой → warning
```

### 4. Нормативные ссылки
```
Проверка: ссылки на НПА найдены в реестре regulatory_documents
- Если replacement_id ≠ null → "Норматив заменён"
- Если last_verified_at > 1 года → "Требуется перепроверка"
```

### Результат

```python
ValidationResult(
    passed=True/False,  # False если есть errors
    issues=[
        Issue(section="Контакты", reason="У Test Person не указан телефон", severity="warning"),
        Issue(section="Нормативы", reason="Ссылка на №531 не найдена", severity="warning"),
    ]
)
```

- `passed=True` → статус `pending_review`
- `passed=False` → статус `auto_validation_failed`

---

## 11. Ревью и утверждение

### Статусы документа

```
processing → pending_review → approved
                 ↓
           auto_validation_failed
                 ↓
             rejected (с замечаниями)
```

### Ревью

```
POST /api/v1/pmla/{id}/review
Body: {reviewer_id, decision: "approved"|"rejected", comments: [{section, reason, severity}]}
```

**Утверждение:**
- Устанавливает `status = "approved"`
- Сохраняет `reviewer_id`, `reviewer_decision`, `reviewer_comments`

**Отклонение:**
- Устанавливает `status = "rejected"`
- Сохраняет замечания по секциям
- Документ доступен для перегенерации

### Скачивание

```
GET /api/v1/pmla/{id}/download      — DOCX (только approved)
GET /api/v1/pmla/{id}/download/pdf   — PDF (только approved)
GET /api/v1/pmla/{id}/preview        — HTML-превью (все статусы)
```

---

## 12. Экспорт документа

### DOCX

Сборка через `python-docx`:

```python
doc = DocxDocument()
doc.add_heading(title, level=0)          # Заголовок документа
doc.add_paragraph(f"Версия: {version}")  # Метаданные
doc.add_paragraph(f"Дата: {generated_at}")

for section_title, content in sections.items():
    doc.add_heading(section_title, level=1)
    for line in content.strip().split("\n"):
        if line.strip():
            doc.add_paragraph(line.strip())

buffer = io.BytesIO()
doc.save(buffer)
return buffer.getvalue()  # bytes → content_docx в БД
```

### PDF

Двухуровневая конвертация:

```
Tier 1: LibreOffice headless (Docker)
  → soffice --headless --convert-to pdf
  → Сохраняет полное форматирование: таблицы, заголовки, шрифты
  → ~239KB для полного документа

Tier 2: fpdf2 fallback (если LibreOffice недоступен)
  → python-docx → текст → fpdf2
  → Без форматирования, только текст
  → ~72KB
```

### Превью

```
GET /api/v1/pmla/{id}/preview
  → python-docx: парсинг DOCX
  → Извлечение секций: заголовки (Heading) + абзацы
  → Возврат JSON: {sections: [{title, content: [строки]}]}
  → Фронтенд: модальное окно с HTML-представлением
```

---

## 13. Архитектура кода

### Backend

```
backend/src/
├── main.py                          # FastAPI app, middleware, роутеры
├── core/
│   └── settings.py                  # pydantic-settings (все env vars)
├── domain/                          # Доменные модели (dataclass)
│   ├── organization/models.py
│   ├── facility/models.py
│   ├── document/models.py
│   └── regulatory/models.py
├── infrastructure/
│   ├── database/
│   │   ├── models.py                # SQLAlchemy модели (13 таблиц)
│   │   └── engine.py                # Async engine + session factory
│   ├── repositories/                # CRUD-операции
│   │   ├── organization_repo.py
│   │   ├── facility_repo.py
│   │   ├── document_repo.py
│   │   ├── regulatory_repo.py
│   │   ├── pmla_sample_repo.py
│   │   └── scenario_matrix_repo.py
│   ├── llm/
│   │   └── providers.py             # LLMProvider + FallbackProvider
│   ├── rag/
│   │   ├── pipeline.py              # DocumentLoader, Chunker, Embedder, VectorStore, Retriever
│   │   ├── sample_indexer.py        # Индексация образцов в ChromaDB
│   │   └── sample_retriever.py      # Поиск + извлечение из образцов
│   ├── pdf/
│   │   └── converter.py             # DOCX → PDF (LibreOffice / fpdf2)
│   ├── geocoding/                   # Яндекс геокодер (не используется)
│   └── references/                  # Справочники аварийных служб (не используется)
├── application/
│   └── services/
│       ├── enhanced_generator.py    # Главный генератор ПМЛА
│       ├── prompts.py               # Промпты для LLM
│       ├── validation.py            # Автоматическая валидация
│       ├── review_service.py        # Ревью и утверждение
│       ├── sample_integration.py    # Координация образцов
│       ├── fallback_texts.py        # Тексты-заглушки
│       ├── calculations/            # Расчётные методики
│       │   ├── explosion_zone.py
│       │   ├── thermal_radiation.py
│       │   ├── toxic_exposure.py
│       │   └── validation.py
│       └── types.py                 # Типы: GeneratedDocument, Issue, ValidationResult
├── api/
│   ├── dependencies.py              # FastAPI Depends (DB, repos)
│   └── routers/                     # REST API
│       ├── organizations.py         # CRUD организаций
│       ├── facilities.py            # CRUD объектов ОПО
│       ├── equipment.py             # CRUD оборудования
│       ├── substances.py            # CRUD веществ
│       ├── persons.py               # CRUD ответственных лиц
│       ├── regulatory.py            # CRUD нормативов
│       ├── pmla.py                  # Генерация, статус, ревью, скачивание
│       ├── pmla_stream.py           # SSE-стриминг прогресса
│       ├── pmla_samples.py          # Загрузка/просмотр/верификация образцов
│       ├── corpus.py                # Загрузка нормативной базы
│       └── scenario_matrix.py       # CRUD матрицы сценариев
├── alembic/versions/                # Миграции БД (001-006)
└── scripts/                         # Утилиты
```

### Frontend

```
frontend/src/
├── App.jsx                          # Маршруты + AuthProvider
├── main.jsx                         # Точка входа
├── index.css                        # Дизайн-система (CSS variables)
├── api.js                           # API-клиент (fetch + Authorization header)
├── context/
│   └── AuthContext.jsx              # Хранение API-ключа
└── pages/
    ├── Login.jsx                    # Страница входа
    ├── Layout.jsx                   # Обёртка: сайдбар + хедер + контент
    ├── Dashboard.jsx                # Дашборд: статистика + последние документы
    ├── Organizations.jsx            # CRUD организаций
    ├── Facilities.jsx               # Список объектов ОПО
    ├── FacilityDetail.jsx           # Детали объекта (оборудование, вещества)
    ├── Persons.jsx                  # CRUD ответственных лиц
    ├── PmlaWizard.jsx               # Мастер генерации ПМЛА
    ├── GenerationProgress.jsx       # SSE-прогресс генерации
    ├── Documents.jsx                # Список документов + ревью
    ├── Regulatory.jsx               # CRUD нормативов
    └── PmlaSamples.jsx              # Управление образцами
```

### Схема данных (PostgreSQL)

```
organizations ──< hazardous_facilities ──< equipment
                      │                      │
                      ├──< hazardous_substances
                      │
                      ├──< documents ──< document_versions
                      │                  ──< calculation_results
                      │
                      └──< responsible_persons (via organization)

regulatory_documents (самоссылка: replacement_id)
pmla_samples (загруженные файлы)
scenario_matrix (матрица сценариев)
```

---

## Резюме: полный цикл от запроса до DOCX

```
1. Пользователь нажимает "Сгенерировать ПМЛА" (фронтенд)
   ↓
2. POST /api/v1/pmla/generate {facility_id}
   ↓
3. Сборка контекста из БД (организация, объект, оборудование, вещества, лица)
   ↓
4. Расчётный блок (взрыв, тепловое, токсическое)
   ↓
5. Выбор сценариев из матрицы (facility_type × hazard_class)
   ↓
6. Для каждого из 29 разделов:
   a. RAG-поиск по нормативной базе (ChromaDB)
   b. RAG-поиск + few-shot из образцов (ChromaDB)
   c. Если content_type="data" → рендеринг Jinja2 шаблона
   d. Если content_type="llm" → промпт → LLM → постобработка → рендеринг
   ↓
7. Автоматическая валидация (разделы, числа, контакты, нормативы)
   ↓
8. Сборка DOCX (python-docx)
   ↓
9. Сохранение в БД (документ + версия + расчёты)
   ↓
10. Возврат {document_id, status, version}
   ↓
11. Пользователь проверяет (превью) → утверждает
   ↓
12. Скачивание DOCX или конвертация в PDF (LibreOffice)
```
