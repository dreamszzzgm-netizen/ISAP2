# План доработки модуля ПМЛА — 8 задач

**Дата:** 2026-07-03  
**Проект:** ISAP — Industrial Safety AI Platform  
**Стек:** FastAPI + SQLAlchemy async + PostgreSQL 16 + Alembic + React + Vite + Docker

---

## Общая статистика

| Метрика | Значение |
|---------|----------|
| Всего задач | 8 |
| Новых файлов | ~15 |
| Изменяемых файлов | ~30 |
| Новых миграций | 5 |
| Новых API-эндпоинтов | ~20 |

---

## Задача 1 — PDF-конвертер (LibreOffice)

**Приоритет:** 1-й | **Сложность:** Низкая | **Время:** ~1 час

### Текущее состояние
- `backend/src/infrastructure/pdf/converter.py` — deux-уровневый конвертер
- Tier 1: `docx2pdf` (MS Word COM) — **всегда падает в Docker**
- Tier 2: `fpdf2` fallback — текст без форматирования
- `docx2pdf` **не в dependencies** — никогда не был в pyproject.toml

### Что делать

| Файл | Действие | Детали |
|------|----------|--------|
| `backend/Dockerfile` | ИЗМЕНИТЬ | Добавить `libreoffice-core libreoffice-writer fonts-liberation fonts-freefont-ttf` |
| `backend/src/infrastructure/pdf/converter.py` | ИЗМЕНИТЬ | Заменить Tier 1: `docx2pdf` → `soffice --headless --convert-to pdf`. fpdf2 остаётся как fallback |
| `backend/src/api/routers/pmla.py` | РАССМОТРЕТЬ | Кэшировать PDF в `content_pdf` (опционально) |

### Конвертер (замена)
```python
def _convert_via_libreoffice(docx_bytes: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = Path(tmpdir) / "input.docx"
        docx_path.write_bytes(docx_bytes)
        result = subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf",
             "--outdir", tmpdir, str(docx_path)],
            capture_output=True, timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"soffice failed: {result.stderr.decode()}")
        return docx_path.with_suffix(".pdf").read_bytes()
```

### Критерии приёмки
- [ ] `GET /pmla/{id}/download/pdf` возвращает валидный PDF
- [ ] PDF открывается в браузере
- [ ] Форматирование DOCX сохранено (таблицы, заголовки)
- [ ] Тест: `test_pdf_conversion_works_without_ms_office()`

---

## Задача 2 — Аутентификация и таблица users

**Приоритет:** 2-й | **Сложность:** Высокая | **Время:** ~4-6 часов

### Текущее состояние
- **Нет таблицы users**, нет auth модуля, нет JWT
- **Нет зависимостей** python-jose, passlib, bcrypt
- CORS открыт: `allow_origins=["http://localhost:3000"]`
- 12 роутеров без авторизации
- Frontend: нет login, нет auth context, нет ProtectedRoute

### Что делать

#### Backend — новые файлы

| Файл | Назначение |
|------|-----------|
| `backend/src/infrastructure/auth/__init__.py` | Auth модуль |
| `backend/src/infrastructure/auth/security.py` | hash_password, verify_password, create/decode JWT |
| `backend/src/infrastructure/repositories/user_repo.py` | UserRepository с get_by_email() |
| `backend/alembic/versions/007_create_users_table.py` | users + user_organizations |
| `backend/src/api/routers/auth.py` | login, register, me, refresh |

#### Backend — изменения

| Файл | Что менять |
|------|-----------|
| `backend/pyproject.toml` | Добавить python-jose, passlib, bcrypt |
| `backend/src/core/settings.py` | jwt_secret_key, jwt_algorithm, token_expire_minutes |
| `backend/src/infrastructure/database/models.py` | UserModel |
| `backend/src/api/dependencies.py` | get_current_user, require_role |
| `backend/src/main.py` | Подключить auth роутер |
| 12 файлов роутеров | Добавить Depends(get_current_active_user) |

#### Frontend — новые файлы

| Файл | Назначение |
|------|-----------|
| `frontend/src/pages/Login.jsx` | Форма логина |
| `frontend/src/context/AuthContext.jsx` | { user, token, login(), logout(), isAuthenticated } |
| `frontend/src/components/ProtectedRoute.jsx` | Редирект на /login если не авторизован |

#### Frontend — изменения

| Файл | Что менять |
|------|-----------|
| `frontend/src/api.js` | Authorization: Bearer header |
| `frontend/src/App.jsx` | AuthProvider + ProtectedRoute |
| `frontend/src/pages/Layout.jsx` | Динамические данные пользователя |

#### Миграция 007
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'operator',  -- operator | reviewer | admin
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE user_organizations (
    user_id UUID REFERENCES users(id),
    organization_id UUID REFERENCES organizations(id),
    PRIMARY KEY (user_id, organization_id)
);
```

### Критерии приёмки
- [ ] `POST /auth/login` возвращает JWT
- [ ] `GET /auth/me` возвращает данные пользователя
- [ ] Все CRUD требуют авторизацию (401 без токена)
- [ ] Пользователь видит только ОПО своих организаций
- [ ] Тест: `test_user_cannot_see_other_organization_data()`

---

## Задача 3 — Геокодинг + аварийные службы

**Приоритет:** 5-й | **Сложность:** Средняя | **Время:** ~3-4 часа

### Текущее состояние
- `YandexGeocoder` **создан, но НЕ используется** (infrastructure/geocoding/)
- `EmergencyServiceFinder` **создан, но НЕ используется** (infrastructure/references/)
- `HazardousFacilityModel` — **нет полей lat/lng**
- Шаблон `04_forces.j2` ожидает `forces_calculation`, `protective_equipment` — **пустые переменные**
- Контекст генерации **не содержит** emergency_services

### Что делать

| Файл | Действие | Детали |
|------|----------|--------|
| `alembic/versions/007_add_coordinates.py` | СОЗДАТЬ | lat/lng в hazardous_facilities |
| `infrastructure/database/models.py` | ИЗМЕНИТЬ | latitude, longitude в HazardousFacilityModel |
| `api/routers/facilities.py` | ИЗМЕНИТЬ | Автогеокодирование при создании ОПО |
| `application/services/enhanced_generator.py` | ИЗМЕНИТЬ | Добавить emergency_services в контекст |
| `api/routers/pmla.py` | ИЗМЕНИТЬ | Emergency services в контекст |
| `api/routers/pmla_stream.py` | ИЗМЕНИТЬ | То же |
| `templates/pmla/sections/04_forces.j2` | ИЗМЕНИТЬ | Таблица ближайших служб |

### Новая миграция
```sql
ALTER TABLE hazardous_facilities
    ADD COLUMN latitude NUMERIC(10, 7),
    ADD COLUMN longitude NUMERIC(10, 7);
CREATE INDEX idx_hf_coords ON hazardous_facilities(latitude, longitude);
```

### Критерии приёмки
- [ ] Добавление ОПО с адресом — автоопределение координат
- [ ] Раздел «Силы и средства» содержит реальные данные из справочника
- [ ] Тест: `test_emergency_services_found_for_tyumen()`

---

## Задача 4 — regulatory_snapshot

**Приоритет:** 3-й | **Сложность:** Средняя | **Время:** ~2-3 часа

### Текущее состояние
- `DocumentVersionModel` — **нет regulatory_snapshot**
- Версии при генерации **не сохраняют** список нормативов
- Версии при ревью сохраняют `input_data={}` (пусто!)
- `validation.py` не проверяет замену/устаревание нормативов

### Что делать

| Файл | Действие |
|------|----------|
| `alembic/versions/008_add_regulatory_snapshot.py` | СОЗДАТЬ — regulatory_snapshot JSONB в document_versions |
| `infrastructure/database/models.py` | ИЗМЕНИТЬ — добавить поле в DocumentVersionModel |
| `application/services/enhanced_generator.py` | ИЗМЕНИТЬ — сохранять снимок нормативов при генерации |
| `application/services/review_service.py` | ИЗМЕНИТЬ — сохранять контекст + snapshot при ревью |
| `application/services/validation.py` | ИЗМЕНИТЬ — проверять replacement_id + last_verified_at |
| `api/routers/pmla.py` | ИЗМЕНИТЬ — добавить GET /{id}/versions |

### Критерии приёмки
- [ ] При создании версии сохраняется regulatory_snapshot
- [ ] Заменённый норматив → блокировка валидации
- [ ] Спорный норматус → requires_regulatory_review
- [ ] Тест: `test_disputed_norm_sets_regulatory_review_flag()`

---

## Задача 5 — Сроки пересмотра ПМЛА

**Приоритет:** 4-й | **Сложность:** Низкая | **Время:** ~2-3 часа

### Текущее состояние
- **Нет полей** approved_at, review_date в documents
- Review service **не сохраняет** дату утверждения
- Dashboard **не показывает** сроки пересмотра

### Что делать

| Файл | Действие |
|------|----------|
| `alembic/versions/009_add_review_dates.py` | СОЗДАТЬ |
| `infrastructure/database/models.py` | ИЗМЕНИТЬ — submitted_at, approved_at, rejected_at |
| `domain/document/models.py` | ИЗМЕНИТЬ — добавить поля в dataclass |
| `application/services/review_service.py` | ИЗМЕНИТЬ — устанавливать даты |
| `api/routers/pmla.py` | ИЗМЕНИТЬ — возвращать даты, добавить /expiring, /overdue |
| `frontend/src/pages/Dashboard.jsx` | ИЗМЕНИТЬ — виджет сроков пересмотра |

### Новые эндпоинты
```
GET /api/v1/pmla/expiring?days=30   — документы с истекающим сроком
GET /api/v1/pmla/overdue            — просроченные документы
```

### Критерии приёмки
- [ ] При утверждении review_date = approved_at + 5 лет
- [ ] `GET /pmla/expiring?days=30` возвращает корректный список
- [ ] Виджет на дашборде с цветовой индикацией
- [ ] Тест: `test_review_date_set_on_approval()`

---

## Задача 6 — Частичная перегенерация разделов

**Приоритет:** 6-й | **Сложность:** Высокая | **Время:** ~6-8 часов

### Текущее состояние
- `generate()` принимает `regenerate_sections`, но **ломает документ** (перезаписывает только выбранные разделы)
- Нет связи отклонение → перегенерация
- Frontend не поддерживает частичную перегенерацию

### Рекомендуемый подход: Section-Level Storage

Хранить каждый раздел отдельно в JSONB, чтобы обновлять только нужные.

| Файл | Действие |
|------|----------|
| `alembic/versions/010_add_document_sections.py` | СОЗДАТЬ — document_sections table |
| `infrastructure/database/models.py` | ИЗМЕНИТЬ — DocumentSectionModel |
| `application/services/enhanced_generator.py` | ИЗМЕНИТЬ — перегенерация отдельных разделов |
| `api/routers/pmla.py` | ИЗМЕНИТЬ — POST /{id}/regenerate |
| `application/services/review_service.py` | ИЗМЕНИТЬ — маппинг section title → ID |
| `frontend/src/pages/Documents.jsx` | ИЗМЕНИТЬ — кнопка перегенерации |
| `frontend/src/pages/PmlaWizard.jsx` | ИЗМЕНИТЬ — пост-отклонение flow |
| `frontend/src/api.js` | ИЗМЕНИТЬ — regenerate() метод |

### Критерии приёмки
- [ ] При отклонении перегенерируются только отклонённые разделы
- [ ] Утверждённые разделы не изменяются
- [ ] После 3 неудачных попыток → статус manual_intervention_required
- [ ] UI позволяет указать замечание к конкретному разделу
- [ ] Тест: `test_partial_regen_does_not_touch_approved_sections()`

---

## Задача 7 — ИИ-агент-ревьюер

**Приоритет:** 7-й | **Сложность:** Средняя | **Время:** ~4-5 часов

### Текущее состояние
- LLM провайдеры работают (complete API)
- Автовалидация правилами — работает
- Нет AI-ревью

### Что делать

| Файл | Действие |
|------|----------|
| `application/services/ai_reviewer.py` | СОЗДАТЬ — AIReviewer с чек-листом |
| `application/services/types.py` | ИЗМЕНИТЬ — AIReviewResult |
| `application/services/enhanced_generator.py` | ИЗМЕНИТЬ — интеграция AI-ревью после Stage D |
| `infrastructure/database/models.py` | ИЗМЕНИТЬ — ai_review поля в DocumentVersionModel |
| `api/routers/pmla.py` | ИЗМЕНИТЬ — GET /{id}/ai-review |
| `core/settings.py` | ИЗМЕНИТЬ — ai_review_enabled, ai_review_temperature |
| `frontend/src/pages/Documents.jsx` | ИЗМЕНИТЬ — показать результат AI-ревью |

### Чек-лист AI-ревьюера (11 пунктов)
1. Каждый сценарий соответствует типу ОПО
2. Для каждого сценария указаны причина, развитие, зоны
3. Зоны поражения совпадают с расчётами
4. Мероприятия привязаны к сценариям
5. СИЗ соответствуют классу опасности
6. Системы защиты учтены
7. Алгоритм действий логичен
8. Ответственные лица присутствуют в данных
9. Порядок оповещения указан
10. Аварийные службы совпадают с справочником
11. Разделы не противоречат друг другу

### Критерии приёмки
- [ ] После валидации запускается AI-ревьюер
- [ ] confidence >= 0.85 → auto-approve
- [ ] confidence < 0.85 → escalate_to_human
- [ ] Спорные нормативы → всегда escalate
- [ ] Тест: `test_ai_reviewer_approves_correct_document()`

---

## Задача 8 — Восстановление версии

**Приоритет:** 8-й | **Сложность:** Средняя | **Время:** ~3-4 часа

### Текущее состояние
- DocumentVersionModel **не хранит content_docx** — при перегенерации старый DOCX теряется
- Нет current_version_id в documents
- Нет эндпоинта восстановления

### Что делать

| Файл | Действие |
|------|----------|
| `alembic/versions/011_add_version_content.py` | СОЗДАТЬ — content_docx в document_versions, current_version_id в documents |
| `infrastructure/database/models.py` | ИЗМЕНИТЬ — добавить поля |
| `infrastructure/repositories/document_repo.py` | ИЗМЕНИТЬ — get_versions(), restore_version() |
| `application/services/enhanced_generator.py` | ИЗМЕНИТЬ — сохранять content_docx в версию |
| `application/services/version_restoration.py` | СОЗДАТЬ — VersionRestorationService |
| `api/routers/pmla.py` | ИЗМЕНИТЬ — GET /versions, POST /restore/{id} |
| `frontend/src/pages/Documents.jsx` | ИЗМЕНИТЬ — история версий + кнопка восстановления |
| `frontend/src/api.js` | ИЗМЕНИТЬ — getVersions(), restoreVersion() |

### Критерии приёмки
- [ ] `POST /pmla/{id}/restore/{version}` создаёт новую версию из старой
- [ ] Старые версии остаются в истории
- [ ] После восстановления статус = pending_review
- [ ] UI показывает кнопку восстановления
- [ ] Тест: `test_restore_creates_new_version_from_old()`

---

## Порядок выполнения

```
1. Задача 1 (PDF)          — 1 час    — нет зависимостей
2. Задача 2 (Auth)         — 5 часов  — нет зависимостей  
3. Задача 4 (Regulatory)   — 3 часа   — нет зависимостей
4. Задача 5 (Review dates) — 3 часа   — зависит от Auth
5. Задача 3 (Geocoding)    — 4 часа   — зависит от Auth
6. Задача 6 (Partial regen)— 7 часов  — нет зависимостей
7. Задача 7 (AI reviewer)  — 5 часов  — зависит от 6
8. Задача 8 (Versioning)   — 4 часа   — зависит от Auth
```

**Общее время:** ~32 часа

---

## Зависимости между задачами

```
Auth (2) ──┬──> Review Dates (5)
            ├──> Geocoding (3)
            └──> Versioning (8)

Partial Regen (6) ──> AI Reviewer (7)

Regulatory Snapshot (4) ──> AI Reviewer (7) (спорные нормативы)
```

---

## Порядок миграций

| # | Файл | Описание |
|---|------|----------|
| 007 | create_users_table | users + user_organizations |
| 008 | add_coordinates | latitude/longitude в hazardous_facilities |
| 009 | add_regulatory_snapshot | regulatory_snapshot в document_versions |
| 010 | add_review_dates | submitted_at, approved_at, rejected_at в documents |
| 011 | add_version_content | content_docx в document_versions, current_version_id в documents |
| 012 | add_document_sections | document_sections table (для частичной перегенерации) |
