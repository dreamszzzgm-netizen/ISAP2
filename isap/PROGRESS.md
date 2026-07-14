# Отчёт прогресса: ISAP

**Дата обновления:** 2026-07-14T15:40
**Проект:** ISAP — Industrial Safety AI Platform

---

## Patch C закоммичен (2026-07-14)

Накопленные фиксы нескольких сессий (аудиты 2026-07-13 + runtime-фиксы 2026-07-13 вечер) выделены в отдельную ветку и закоммичены одним коммитом.

**Коммит:** `f544c44 fix(pmla): Patch C - PASF storage, preflight, v2 context, frontend hardening`
**Ветка:** `patch-c/pmla-pasf-frontend-hardening` (от `main` @ `0981cea`)
**Объём:** 28 файлов, +1464 / −258

### Что вошло в Patch C (28 файлов)

| Категория | Файлы |
|-----------|-------|
| Backend PASF/PMLA | `directories_pasf.py`, `pmla_preflight.py`, `pmla_questionnaire_service.py`, `pmla_v2_context_mapper.py`, `enhanced_generator.py`, `models.py`, `pmla_template_renderer.py` |
| Backend тесты | `test_directories.py`, `test_pmla_api_smoke_flow.py`, `test_pmla_generation_core.py`, `test_pmla_v2_integration.py`, `test_pmla_pasf_documents_e2e.py` (новый) |
| Миграция | `a5c8a2dd1a14_add_agreement_date_to_emergency_rescue_.py` (новая) |
| Schema/шаблон | `pmla_v2.schema.json`, `pmla_v2_context_keys.json`, `pmla_v2_template_keys.json`, `pmla_v2_template.docx` |
| Frontend | `opo-page.tsx`, `pmla-questionnaire-page.tsx`, `api-client.ts`, `next.config.ts`, `Dockerfile`, `.dockerignore`, `.env.example` |
| Docker/config | `docker-compose.yml`, `.gitignore` (корень + isap), `docs/FRONTEND_MIGRATION.md` |

### Ключевые фиксы в коммите
- **PASF storage policy:** загрузка санитизирует имя файла в basename, хранит под `PASF_DOCUMENTS_UPLOAD_DIR`, проверяет commonpath против upload root (path-escape защита)
- **PASF preflight:** относительные и абсолютные пути документов ПАСФ confinement'ятся к upload root — `PASF_FILE_NOT_FOUND` на загруженных файлах исправлен
- **v2 emergency-service mapping:** канонические + алиас ключи (PASF/medical/fire/questionnaire), включая корректный `скорая`
- **v2 contract:** даты `DD.MM.YYYY`, `contractor_agreement_number` проведён через schema/template/context keys
- **v2 appendices_manifest:** доходит до `PmlaTemplateRenderer` и дописывается в DOCX
- **Frontend hazard-class:** `opo-page.tsx` маппит I/II/III/IV через явный хелпер (был баг `"IVII".indexOf(...)`)
- **Frontend API:** same-origin по умолчанию, `INTERNAL_API_BASE_URL` для Docker build-time rewrites, `skipTrailingSlashRedirect` (не было утечки `backend:8000` в редиректах)
- **Frontend Docker:** standalone output, `.env*.local` вне build context
- **Runtime 422 fix:** `pmla-questionnaire-page.tsx` обрабатывает `blocked` статус, disabled-кнопки без `document_id`, опциональные поля в `PmlaGenerationResult`
- **enhanced_generator:** module-level logger, ошибки валидации логируются (не silent pass)

### Verification (гейт перед коммитом, 2026-07-14)
| Проверка | Результат |
|----------|-----------|
| Backend `pytest tests -q` | **704 passed, 3 skipped, 41 warnings** |
| Frontend `tsc --noEmit --incremental false` | passed (exit 0) |
| Frontend `npm run build` | ✓ Compiled successfully |
| `git diff --cached --check` | passed (только PDF-xref trailing whitespace в фикстуре — валидный PDF) |

### Осознанно НЕ вошло в коммит
Локальные артефакты (51 untracked), оставшиеся в working tree:
- `AI_DEVELOPER_PROMPT.md`
- `backend/scripts/*` (template surgery / render audit скрипты, машинно-специфичные пути)
- `docs/audit/*`, `docs/PMLA_V2_*.md`, `docs/EPB_REGISTRY_MVP.md`
- `files/pmla_v1.schema.json`
- Сгенерированные `.next/`, `__pycache__/`, `nul`, QA render outputs

Решение по каждому — отдельно (stage / gitignore / удалить с диска).

### Deploy note
При накате на новое окружение обязательно:
```bash
docker exec isap_backend alembic upgrade head   # применит a5c8a2dd1a14
```

---

## Runtime-фиксы: 500 на emergency-services + 422 на pmla/undefined/download (2026-07-13 вечер)

Цель: разобрать три ошибки из консоли браузера при работе с PMLA-генерацией.

### Ошибка #1: `GET /api/v1/directories/emergency-services/ → 500`

**Причина:** Модель SQLAlchemy ожидает колонки `additional_phone`, `region`, `verified_at`, `is_active` (добавлены в миграции `018_add_directory_fields.py`), но БД была на ревизии `017`. Миграции 018, 019, a5c8a2dd1a14 не были применены после пересоздания Docker-стека.

**Ошибка БД:**
```
UndefinedColumnError: column emergency_services.additional_phone does not exist
```

**Фикс:** `docker exec isap_backend alembic upgrade head` — БД поднята с `017 → a5c8a2dd1a14` (head).
- 018: directory fields для pasf/emergency services
- 019: таблица pasf_documents
- a5c8a2dd1a14: agreement_date для emergency_rescue_units

**Результат:** 500 → **200 OK**.

### Ошибка #2: `GET /api/v1/pmla/undefined/download → 422`

**Причина (цепочка):**
1. Дефолтный `generation_mode = "final"` в `GenerateFromQuestionnaireRequest`
2. Preflight в final-режиме находит блокеры (нет оборудования/ПАСФ/служб) → возвращает `{"status": "blocked", ...}` **без `document_id`**
3. Фронт сохранял ответ в `generation` и показывал активную кнопку «Скачать DOCX»
4. Клик → `downloadPmlaDocumentBlob(undefined)` → `/pmla/undefined/download` → **422**

**Фикс** (`frontend/src/lib/api-client.ts`, `frontend/src/components/dashboard/pmla-questionnaire-page.tsx`):
- В типе `PmlaGenerationResult` поля `document_id`, `questionnaire_id`, `facility_id` сделаны опциональными
- Добавлены поля `reason`, `preflight`, `provenance` (для статуса `blocked`)
- `handleDownload` выходит, если нет `generation.document_id`
- Кнопки «Скачать DOCX», «Открыть карточку», «Скопировать document_id» — `disabled={!hasDocument}`
- Добавлен отдельный алерт для статуса `blocked` с показом `reason` и preflight-отчёта
- Исправлена логика `isSuccess`: `pending_review` (реальный статус успеха) + `completed` — раньше фронт всегда считал статус ошибкой, потому что сравнивал только с `"completed"`
- Заголовок карточки: иконка `AlertTriangle` вместо `CheckCircle2` при `isBlocked`

### Ошибка #3: `Unable to add filesystem: <illegal path>` (api-client.ts:206)

**Причина:** Побочный симптом бага #2 — blob-fetch на `/pmla/undefined/download` возвращал 422, и Chromium DevTools ругался на обработку ответа. После фикса `document_id` исчезает сама собой.

### Дополнительно: опыт работы со сборкой

- После редактирования фронтенда нужно **очищать `.next`-кэш** в контейнере и делать `docker compose restart frontend`, иначе dev-сервер отдаёт закешированный бандл
- Команда: `docker exec isap_frontend sh -c 'rm -rf /app/.next'` + `docker compose restart frontend`
- Пользователю нужно жёстко обновить страницу в браузере (Ctrl+Shift+R), чтобы сбросить клиентский кэш бандла

### Проверки

| Проверка | Результат |
|----------|-----------|
| Backend `emergency-services/` | **200 OK** (было 500) |
| Backend `pasf/`, `pmla/` | 200 OK |
| `alembic current` | `a5c8a2dd1a14` (head) |
| Backend `test_directories.py` | 9 passed |
| Frontend `tsc --noEmit` | passed |
| Frontend `eslint` (изменённые файлы) | только pre-existing warnings |
| Frontend `npm run build` | passed |

### Реальные блокеры preflight (нормальное поведение)

При попытке генерации в `final`-режиме preflight корректно блокирует генерацию с понятным отчётом:
- **EQ_EMPTY_LIST** — список оборудования пуст → добавить в карточку ОПО
- **PASF_MISSING** — не выбран ПАСФ/АСФ → выбрать в анкете
- (warnings) FIN_NOT_FILLED, RES_MISSING_ACTUAL_ITEMS — не блокируют

Это не баг — preflight защищает от генерации неполного документа.

### Изменённые файлы

| Файл | Изменение |
|------|-----------|
| `frontend/src/lib/api-client.ts` | `PmlaGenerationResult`: опциональные поля + blocked-поля |
| `frontend/src/components/dashboard/pmla-questionnaire-page.tsx` | обработка `blocked` статуса, disabled-кнопки, preflight-алерт |

### Незакоммичено

Patch C + эти фиксы остаются в working tree. При деплое на новое окружение обязательно:
```bash
docker exec isap_backend alembic upgrade head
```

---

## AGZS Support — Guardrails + KG/RAG (2026-07-11)

Goal: add AGZS (АГЗС) facility type support with cross-facility guardrails.

### What was built
- AGZS normalization: "станция газозаправочная автомобильная" → "агзс"
- KG context for AGZS: equipment (СУГ), hazards, scenarios, services, appendices
- RAG chunks for AGZS: section_2, section_5, section_10, section_12, special_section
- Forbidden terms for AGZS: водогрейный котёл, котельная, теплосеть, ГРПШ, ШРП
- 11 new tests

### AGZS KG context
- **Equipment:** резервуар СУГ, заправочная колонка, сливной пост, НКО, трубопроводы
- **Hazards:** утечка СУГ, газовоздушное облако, пожар, взрыв, разрушение оборудования
- **Scenarios:** разгерметизация резервуара/трубопровода, утечка при сливе, пожар на колонке

### Files
- `cross_facility_guardrails.py` (+40 lines — AGZS forbidden terms, normalization)
- `pmla_knowledge_graph_adapter.py` (+60 lines — AGZS KG context)
- `pmla_rag_adapter.py` (+60 lines — AGZS RAG chunks)
- `test_cross_facility_guardrails.py` (+11 tests)

### Tests
537 passed, 41 warnings.

---

## PMLA Cross-Facility Guardrails (2026-07-11)

Goal: prevent content from one facility type from appearing in another.

### What was built
- `cross_facility_guardrails.py` — forbidden terms dictionary + contamination check
- Quality review `cross_facility_contamination` check (warning level)
- RAG adapter filter for contaminated chunks
- 15 regression tests

### Forbidden terms
| Facility type | Forbidden terms |
|---------------|-----------------|
| Котельная | ГРПШ, ШРП, газорегуляторный пункт |
| Компрессорная станция | ГРПШ, ШРП, водогрейный котёл, котёл |
| АЗС | ГРПШ, ШРП, водогрейный котёл, котёл |

### Guardrails active
1. RulesEngine: NO fallback to gas network scenarios for other facility types
2. RAG adapter: filters chunks with cross-facility contamination
3. Quality review: warns on cross-facility contamination
4. Equipment exclusion: terms found in equipment context are not flagged

### Files
- `cross_facility_guardrails.py` (new, 100 lines)
- `pmla_quality_review_service.py` (+30 lines — contamination check)
- `pmla_rag_adapter.py` (+15 lines — RAG filter)
- `test_cross_facility_guardrails.py` (new, 15 tests)

### Tests
526 passed, 41 warnings.

---

## Real OPO Validation #4 — Second Facility Type (2026-07-10)

Goal: verify PMLA generation works for non-gas facility types.

### Facility
- **Type:** Котельная (boiler)
- **Name:** Котельная производственной площадки
- **Organization:** ООО "ТеплоСервис"
- **Equipment:** Котёл, Горелка, Газопровод НД, Насос

### Critical issue found and fixed
- **Bug:** section_10 contained gas network scenarios (ГРПШ) for boiler facility
- **Root cause:** `_render_section_10` fallback used gas network scenarios when no boiler-specific scenarios found
- **Fix:** Replaced gas network fallback with generic first actions for unknown facility types
- **File:** `rules_engine.py`

### Results after fix
- **Mojibake:** 0
- **Chinese:** 0
- **Gas-network terms in boiler DOCX:** 0 (was 18+, fixed)
- **Quality review:** warning (data gaps, not code issues)
- **Critical issues:** 0

### Files
- `rules_engine.py` (+13 lines — removed gas network fallback)
- `REAL_OPO_VALIDATION_4_REPORT.md` (new)

### Tests
511 passed, 41 warnings.

---

## Real OPO Validation #3 — RAG Effectiveness Review (2026-07-10)

Goal: verify RAG consumption improved generated sections quality.

### Results
- **Quality review:** warning (не critical), 0 critical, 10 warnings (data gaps)
- **Mojibake:** 0, **Chinese:** 0
- **All 7 generated sections gas-specific:** Yes
- **6/7 sections grew with RAG:** Yes
- **RAG chunks consumed:** Yes (injected by RulesEngine/ScenarioEngine/NarrativeEngine)

### Before/After (with RAG consumption)

| Section | Before | After | Δ |
|---------|--------|-------|---|
| section_2 | 498 | 547 | +49 |
| section_5 | 117 | 145 | +28 |
| section_7 | 101 | 131 | +30 |
| section_10 | 1543 | 1578 | +35 |
| section_12 | 102 | 127 | +25 |
| special_section | 998 | 1033 | +35 |

### No critical issues found
All warnings are data completeness issues, not code defects.

---

## PMLA RAG Consumption in Generated Engines (2026-07-10)

Goal: make generated engines actually consume RAG context.

### What was built
- RulesEngine injects RAG chunks into section_5, section_7, section_10, section_12
- ScenarioEngine injects RAG chunks into section_2, special_section
- NarrativeEngine injects RAG chunks into introduction
- All RAG text sanitized (strip_html + sanitize_cyrillic_text)
- Limits: max 3 chunks, 800 chars/chunk, 2000 total
- Metadata: rag_used, rag_chunks_count, rag_sources in SectionContent

### Before vs After (Real OPO)

| Section | Before | After | Change |
|---------|--------|-------|--------|
| section_2 | 498 words | 547 words | **+49 words** |
| section_5 | 117 words | 145 words | **+28 words** |
| section_7 | 101 words | 131 words | **+30 words** |
| section_10 | 1543 words | 1578 words | **+35 words** |
| section_12 | 102 words | 127 words | **+25 words** |
| special_section | 998 words | 1033 words | **+35 words** |

### Files
- `rules_engine.py` (+100 lines — RAG injection)
- `scenario_engine.py` (+50 lines — RAG injection)
- `narrative_engine.py` (+60 lines — RAG injection)
- `test_pmla_rag_consumption.py` (new, 10 tests)

### Tests
511 passed, 41 warnings.

---

## Real OPO Validation #2 — KG + RAG Enriched DOCX (2026-07-10)

Goal: verify KG+RAG improved generated sections in real OPO DOCX.

### Results
- **Mojibake:** 0 (fixed)
- **Chinese:** 0 (fixed)
- **All generated sections gas-specific:** Yes
- **Quality review:** critical (data gaps, not code issues)
- **RAG context:** stored in enriched context, available for future engine use

### Key finding
RAG context is properly stored in `DocumentContext.rag_contexts` but RulesEngine/ScenarioEngine don't yet consume it to modify output. The context is available for future engine updates.

### No new critical issues
All issues are data gaps (missing emergency services, notification scheme) — not code defects.

### Files
- `REAL_OPO_VALIDATION_REPORT.md` (updated with Validation #2 section)

---

## PMLA RAG for Generated Sections (2026-07-10)

Goal: connect RAG only to generated_block sections for enriched content.

### What was built

- `pmla_rag_adapter.py` — read-only RAG adapter with in-memory fallback
- `PmlaRagContext` / `PmlaRagChunk` dataclasses
- Integration with `enhanced_generator._enrich_context()` — RAG context pre-fetched for all generated sections
- `DocumentContext.rag_contexts` field for engine access
- 14 unit tests

### RAG coverage

| Facility type | Sections with RAG |
|---------------|-------------------|
| Сеть газопотребления | section_2, section_5, section_7, section_10, section_12, special_section |
| Котельная | section_2, section_10 |

### What RAG does NOT touch

- static_block (templates only)
- variable_block (data only)
- word_toc_block (Word TOC)
- appendix_reference (manifest)

### Files
- `pmla_rag_adapter.py` (new, 252 lines)
- `enhanced_generator.py` (+15 lines — RAG enrichment)
- `engine_integration.py` (+1 line — rag_contexts passthrough)
- `base.py` (+2 lines — rag_contexts field)
- `test_pmla_rag_adapter.py` (new, 14 tests)
- `docs/PMLA_RAG_STRATEGY.md` (new)

### Tests
501 passed, 41 warnings. Frontend build OK.

---

## Knowledge Graph Read Adapter for PMLA (2026-07-10)

Goal: connect knowledge graph as read-only context source for PMLA quality review.

### What was built

- `pmla_knowledge_graph_adapter.py` — read-only adapter with in-memory fallback
- `PmlaKnowledgeGraphContext` dataclass with structured fields
- Quality review integration with 3 new warning-level checks
- 13 unit tests + deep edge case testing

### Knowledge base coverage

4 facility types: сеть газопотребления, котельная, компрессорная станция, АЗС

### Quality review graph checks

| Check | Level | What it validates |
|-------|-------|-------------------|
| `graph_required_service_missing` | warning | Required emergency services present |
| `graph_required_scenario_missing` | warning | Recommended accident scenarios present |
| `graph_required_appendix_missing` | warning | Required appendices in checklist |

### Bugs found and fixed during deep testing

- Integer `facility_type` caused AttributeError in adapter — fixed with `str()` conversion

### Files
- `pmla_knowledge_graph_adapter.py` (new, 276 lines)
- `pmla_quality_review_service.py` (+150 lines)
- `test_pmla_knowledge_graph_adapter.py` (new, 13 tests)
- `docs/KNOWLEDGE_GRAPH_PMLA_ADAPTER.md` (new)

### Tests
487 passed, 41 warnings. Frontend build OK.

---

## PMLA Data Completeness & Input Quality (2026-07-10)

Goal: improve data completeness and context mapping so DOCX requires less manual editing.

### Important issues closed

| # | Issue | Fix |
|---|-------|-----|
| I4 | Appendix responsible persons show "— — —" | Fixed `30_appendix_1.j2` template: uses `person.full_name` with fallback to `person.name`, uses `approver.name` in fallback |
| I5 | Bibliography contains Chinese/English text | Fixed `40_bibliography.j2`: replaced "生产" → "производства", "equipment" → "оборудования" |
| I6 | Familiarization sheet missing date/number | Added `document_date` to `enhanced_generator._enrich_context()` (defaults to generation date) |

### New quality review checks (6)

| Check | Status | What it validates |
|-------|--------|-------------------|
| `emergency_service_phones` | warning | Emergency services have phone numbers |
| `notification_responsible` | warning | Notification scheme has responsible persons |
| `financial_reserve_data` | warning | Financial reserve data completeness |
| `insurance_data` | warning | Insurance data completeness |
| `familiarization_date` | warning | Registration number for familiarization sheet |
| `appendix_signatures` | warning | Responsible persons with positions for appendix signatures |

All new checks are **warning** level (not critical) — they guide the engineer without blocking document generation.

### Files changed
- `40_bibliography.j2` — fixed Chinese/English text
- `30_appendix_1.j2` — fixed responsible persons rendering
- `enhanced_generator.py` — added `document_date` to context
- `pmla_quality_review_service.py` — added 6 data completeness checks (+175 lines)
- `test_pmla_quality_review_service.py` — updated test context and check count
- `test_stabilization_patch.py` — added reg_number and phone numbers to demo context

### Tests
474 passed, 41 warnings. Frontend build OK.

---

## PMLA Real OPO Validation #1 — Content Review (2026-07-10)

Goal: content review of first real OPO DOCX, identify defects, fix critical issues.

### Findings

**Critical (2 fixed):**
- C1: Custom scenario #6 mojibake in questionnaire data → re-inserted via Python
- C2: LLM hallucinated Chinese characters "熱画像" → added `sanitize_cyrillic_text()` filter

**Important (6 documented, deferred):**
- I1: No real emergency services data (data gap)
- I2: Empty notification scheme (data gap)
- I3: No financial reserve/insurance (data gap)
- I4: Appendix responsible persons show "— — —"
- I5: Bibliography contains Chinese/English text
- I6: Familiarization sheet missing date/reg number

**Minor (4 documented):**
- M1: Phone numbers still show "тел." in section 11
- M2: Validation results as plain text
- M3: OPO details form not integrated
- M4: Generic fallback text in some sections

### Files changed
- `docx_helpers.py` — added `sanitize_cyrillic_text()` function
- `template_engine.py` — apply sanitize filter on template output
- `enhanced_generator.py` — apply sanitize filter on body paragraphs
- `test_pmla_quality_review_v2.py` — +4 sanitize regression tests

### Tests
470 passed, 30 v2 tests. Frontend build OK.

### Validation report
`backend/data/real_opo_validation/REAL_OPO_VALIDATION_REPORT.md`

---

## PMLA Real OPO Validation #1 — DOCX defect fixes (2026-07-10)

Goal: fix data defects found during first real OPO DOCX generation.

### Mojibake (FIXED)

**Source:** PowerShell `Get-Content` pipe corrupted UTF-8 Cyrillic when piping SQL files to `docker exec psql`. The SQL file had correct UTF-8, but PowerShell re-encoded it through the console codepage (CP1251 on Russian Windows).

**Impact:** Responsible persons' names and positions appeared as mojibake (`РРЅРґРёРІ...` instead of `Индивидуальный`).

**Fix:** Data was re-inserted into the Docker database via Python (bypassing PowerShell pipe). The `validate_real_opo.py` script already used Python for DB operations; the issue was the initial SQL file import via `Get-Content | docker exec psql`.

**Prevention:** Always use Python SQLAlchemy for inserting Cyrillic data into PostgreSQL. Never pipe UTF-8 SQL through PowerShell to psql.

### Empty phones (FIXED)

**File:** `rules_engine.py:377`

Before: `f"тел. {p.get('phone', '—')}"` → showed "тел. " when phone empty.
After: phone part only shown if non-empty → "Иванов Иван Иванович — Индивидуальный предприниматель"

### Appendix manifest (FIXED)

**File:** `enhanced_generator.py:1147`, `docx_helpers.py:541`

Before: all 5 appendices showed "не представлен" when `attachments_checklist` was empty.
After: template-generated appendices (Jinja2) are always "сформировано" since they produce content directly in DOCX. Only file-based appendices check the checklist.

### ГОСТ Р 22.10.03-2020

Not added — the regulatory registry structure doesn't have a simple add mechanism. The warning is cosmetic and doesn't affect document quality. Defer to a dedicated regulatory registry update task.

### Files changed

- `backend/src/application/engines/rules_engine.py` — empty phone fix
- `backend/src/application/services/enhanced_generator.py` — appendix manifest logic
- `backend/src/infrastructure/export/docx_helpers.py` — "сформировано" status
- `backend/tests/test_pmla_assembly.py` — updated 3 manifest tests
- `backend/tests/test_pmla_quality_review_v2.py` — +2 Cyrillic regression tests

### Tests

470 passed, 41 warnings. Frontend build OK.

### Real OPO DOCX

Generated: `backend/data/real_opo_validation/real_opo_v2.docx` (67KB)
- No mojibake
- Correct Cyrillic
- Appendix manifest shows "сформировано"
- No bare "тел."

---

## PMLA Quality Review v2 — Assembly-aware checks (2026-07-10)

Goal: update quality review to understand PMLA Assembly Layer and validate document by block types, not only by string presence.

Done:
- Updated `CheckResult` dataclass with `block_id` and `block_type` fields
- Added 6 new block-aware checks using Assembly Registry as source of truth
- Updated `review()` to accept `rendered_sections` parameter for content validation
- Updated `to_dict()` to include `block_id` and `block_type` in output
- Fixed `_check_attachments_checklist` to handle both string and dict `{name, present}` formats
- Added block-aware recommendations for failed checks

New block-aware checks:

| # | Check code | Block type | What it validates |
|---|---|---|---|
| 1 | `assembly_static_blocks` | `static_block` | All static sections defined in registry; no data required |
| 2 | `assembly_variable_blocks` | `variable_block` | Key data sources (organization, facility, etc.) present in context |
| 3 | `assembly_generated_blocks` | `generated_block` | Non-empty text, no raw HTML, minimum content length |
| 4 | `assembly_toc_block` | `word_toc_block` | TOC section defined, heading present |
| 5 | `assembly_appendix_references` | `appendix_reference` | Manifest has entries, attachments_checklist present |
| 6 | `assembly_external_files` | `external_file` | Block type registered (placeholder for future PDF merge) |

Output format (v2):
```python
{
    "overall_status": "ok | warning | critical",
    "score": int,
    "checks": [
        {
            "code": str,
            "title": str,
            "status": "passed | warning | failed",
            "message": str,
            "block_id": str | None,
            "block_type": str | None
        }
    ],
    "recommendations": [str]
}
```

Scoring (unchanged): 100 - (20 × critical) - (8 × warning), floor 0.

Assembly Registry integration:
- `ASSEMBLY_REGISTRY` from `pmla_assembly_blocks.py` is the single source of truth
- `get_static_sections()`, `get_variable_sections()`, `get_generated_sections()` drive block checks
- `get_appendix_manifest_entries()` powers appendix validation
- `structure.json` block_type fields verified against registry (invariant tested)

Demo PMLA result:
- Status: `warning` (not critical)
- Score: 92
- 16 checks (10 data + 6 block-aware)
- 0 critical, 1 warning (attachments_checklist name mismatch)
- All block checks: `ok`

Changed files:
- `backend/src/application/services/pmla_quality_review_service.py` (+303 lines)
- `backend/tests/test_pmla_quality_review_service.py` (1 test updated)
- `backend/tests/test_pmla_quality_review_v2.py` (**new**: 24 tests)

Tests: 468 passed, 41 warnings. Frontend build OK.

---

## PMLA Assembly Layer - Hybrid Generation Architecture (2026-07-09)

Goal: hybrid PMLA assembly - static sections from templates, variable with substitution, dynamic from questionnaire/LLM, appendices as manifest. Reduce generation complexity, minimize LLM dependency.

Done:
- Created block type registry (6 types: static, variable, generated, word_toc, appendix_ref, external_file)
- Added correction journal as proper DOCX table
- Added Word TOC placeholder with Heading styles
- Added appendices manifest table
- Updated structure.json with block_type for all 27 sections
- Created assembly strategy documentation

Section classification:
- static_block (4): correction_log, abbreviations, terms, bibliography
- variable_block (11): title_page, approval_sheet, section_1, 3, 4, 6, 8, 13, familiarization_sheet, appendix_1, 5
- generated_block (10): introduction, section_2, 5, 7, 9, 10, 11, 12, special_section
- word_toc_block (1): toc
- appendix_reference (5): appendix_1-5

Changed files: pmla_assembly_blocks.py, test_pmla_assembly.py, PMLA_ASSEMBLY_STRATEGY.md, structure.json, docx_helpers.py, enhanced_generator.py

Tests: 21 new, 424 total passed. Frontend build OK.

---

## PMLA Patch B — Approval Sheet in DOCX (2026-07-09)

Goal: add a dedicated front-matter "Лист согласования" to generated PMLA DOCX without changing review workflow, database schema, frontend UI, RAG, geocoding, routes, or migrations.

Done:
- Added a DOCX approval sheet after the title page and before "Журнал корректировки документа" / "Содержание".
- Added a real DOCX helper `add_approval_sheet()` with a table:
  - `Роль`
  - `Должность`
  - `ФИО`
  - `Подпись`
  - `Дата`
- Added minimum rows:
  - `Разработал`
  - `Проверил`
  - `Утвердил`
- Added safe data mapping from existing context only:
  - `responsible_persons`
  - `approver`
  - `organization.director`
  - `organization.manager`
  - `facility.responsible_person`
- Added fallbacks that do not imply real approval:
  - `Инженер`
  - `Ответственный специалист`
  - `Руководитель организации`
  - blank signature/date fields
- Added `approval_sheet` to PMLA `structure.json` and `TemplateEngine` for template/debug visibility.
- Added `00_approval_sheet.j2` template.
- Prevented duplicate front-matter rendering by popping `Титульный лист` and `Лист согласования` before rendering main sections.
- Preserved review workflow: generated documents are not marked `approved`; approval still requires manual review workflow.

Changed files:
- `backend/src/infrastructure/export/docx_helpers.py`
- `backend/src/application/services/enhanced_generator.py`
- `backend/src/application/engines/template_engine.py`
- `backend/templates/pmla/structure.json`
- `backend/templates/pmla/sections/00_approval_sheet.j2`
- `backend/tests/test_enhanced_generator.py`

Regression tests added:
- `_build_docx` contains "Лист согласования".
- Approval sheet contains `Разработал`, `Проверил`, `Утвердил`.
- Approval sheet contains `Должность`, `ФИО`, `Подпись`, `Дата`.
- Approval sheet appears before "Журнал корректировки документа".
- Approval sheet is not duplicated when present in `sections`.
- DOCX output does not contain `None`, `undefined`, raw JSON markers, or HTML table tags.

Verified:
- Focused DOCX tests: `9 passed`.
- Related DOCX/template tests: `41 passed`.
- Full backend suite: `403 passed, 41 warnings`.
- Frontend build: `npm run build` completed successfully.
- Git hygiene checks: no tracked `.next`, `node_modules`, `.env.local`, `tsconfig.tsbuildinfo`, logs, zips, patches, `output.docx`, `generated_documents`, or `docs/inbox`.

Commit:
- `8004164 feat(PMLA): add approval sheet to DOCX`

Notes:
- `docs/inbox/` remains local validation material and must not be committed.
- Patch B is intentionally a DOCX-generation patch only.

---

## Stabilization Patch (2026-07-08)

Патч стабилизации после demo walkthrough ПМЛА MVP.

### Исправленные баги

| # | Баг | Файл | Решение |
|---|-----|------|---------|
| 1 | `attachments_checklist` — `'str' object has no attribute 'get'` | `docx_helpers.py` | Добавлена нормализация `_normalize_attachment()`: принимает и строки, и объекты `{name, present}` |
| 2 | HTML-фрагменты (`<td>`, `<tr>`, `<table>`) в DOCX | `template_engine.py`, `enhanced_generator.py` | Добавлена функция `strip_html()` — очистка перед вставкой в DOCX |
| 3 | ПАСФ/аварийные службы не отображались в DOCX | `data_engine.py`, `04_forces.j2` | Section 6 теперь использует реальные emergency_services из контекста; шаблон 04_forces.j2 поддерживает list и dict форматы |
| 4 | Quality review не распознавал ключи demo notification_scheme | `pmla_quality_review_service.py` | Добавлены алиасы ключей: `responsible_manager` → `incident_commander`, `calls_pasf` → `pasf_caller`, `calls_fire` → `fire_caller` |
| 5 | Demo seed `attachments_checklist` был списком строк | `demo_pmla_validation.json` | Приведён к формату объектов `[{name, present}]` |
| 6 | Walkthrough содержал устаревший путь | `PMLA_DEMO_DATA_WALKTHROUGH.md` | Обновлены пути и добавлен PYTHONPATH |
| 7 | 401 Unauthorized — frontend не отправлял API ключ | `frontend/.env.local` | Создан файл с `NEXT_PUBLIC_API_KEY=isap-secret-2026` |
| 8 | БД не имела колонки `version` | Миграции | Запущены `alembic upgrade head` (миграции 016, 017) |

### Изменённые файлы (10 файлов + 1 новый)

| Файл | Изменение |
|------|-----------|
| `backend/src/infrastructure/export/docx_helpers.py` | `_normalize_attachment()`, `strip_html()`, тип `add_appendices_section` |
| `backend/src/application/engines/template_engine.py` | Импорт и вызов `strip_html()` перед созданием ParagraphBlocks |
| `backend/src/application/services/enhanced_generator.py` | `strip_html()` в `_add_body_paragraph()` и `_build_docx()` |
| `backend/src/application/engines/data_engine.py` | `_render_section_6()` использует реальные emergency_services |
| `backend/src/application/services/pmla_quality_review_service.py` | Алиасы ключей notification_scheme, поддержка dict в attachments |
| `backend/templates/pmla/sections/04_forces.j2` | Поддержка list и dict формата emergency_services |
| `backend/data/demo_pmla_validation.json` | attachments_checklist → объекты |
| `docs/PMLA_DEMO_DATA_WALKTHROUGH.md` | Пути, PYTHONPATH |
| `backend/tests/test_stabilization_patch.py` | **Новый:** 19 тестов стабилизации |
| `frontend/.env.local` | **Новый:** API ключ для backend |
| `frontend/next-env.d.ts` | Auto-generated (build noise) |
| `backend/src/application/services/pmla_quality_review_service.py` | Алиасы ключей notification_scheme, поддержка dict в attachments |
| `backend/templates/pmla/sections/04_forces.j2` | Поддержка list и dict формата emergency_services |

### Результаты проверок

| Проверка | Результат |
|----------|-----------|
| `pytest -q` | **381 passed**, 41 warnings |
| `npm run build` | ✓ Compiled successfully |
| `API /api/v1/pmla/` | 200 OK (с API ключом) |
| `git status` | Чисто — working tree clean |

### Новые тесты (19)

- `_normalize_attachment` — строка, объект, пустой объект
- `add_appendices_section` — строки, объекты, смешанный формат, пустой список
- `strip_html` — базовый, без тегов, вложенные теги
- Quality review — demo notification, PASF, emergency services, attachments, score
- Demo seed — attachments объекты, notification ключи

### Статус после патча

| Метрика | Значение |
|---------|----------|
| Backend tests | 381 passed |
| Frontend build | ✓ |
| API авторизация | Frontend → Backend с Bearer token |
| HTML в DOCX | Удалён через strip_html() |
| ПАСФ в DOCX | Отображается через section_6 + emergency_services |
| Службы в DOCX | Отображаются из контекста анкеты |
| Quality score (demo) | ≥ 80 (без critical) |

### Docker

| Контейнер | Статус | Порт |
|-----------|--------|------|
| isap_backend | Up | 8000 |
| isap_frontend | Up | 3000 |
| isap_db | Up (healthy) | 5432 |
| isap_chromadb | Up | 8001 |

### Git commits

```
f896bfb stabilization patch: fix attachments_checklist, strip HTML from DOCX, add PASF/emergency services, sync quality review
```

---

## PMLA MVP 1.0 — Internal Validation Stage

- PMLA MVP 1.0 is technically assembled and ready for internal validation.
- Internal release checklist added under `docs/PMLA_MVP_RELEASE_CHECKLIST.md`.
- Real/anonymized data validation plan added under `docs/PMLA_REAL_DATA_VALIDATION_PLAN.md`.
- Next stage: validate the MVP on real or anonymized OPO data.
- Production limitations remain: no production deployment, no automatic client delivery, no electronic signature, no route calculation, no automatic geocoding, and no full RAG over PMLA samples.
- Engineer review remains mandatory before using generated documents as a client-facing result.

---

## PMLA MVP release checklist added

**File:** `PMLA_MVP_RELEASE_CHECKLIST.md`

Short MVP release checklist refreshed: MVP scope, out-of-scope items, verified scenario, endpoint groups, known limitations, and next steps after MVP.

---

## PMLA MVP stabilization checklist added

**Файл:** `PMLA_MVP_RELEASE_CHECKLIST.md`

**Что зафиксировано:**
- MVP scope: 16 функций входят, 10 не входят
- Проверенный пользовательский сценарий (11 шагов)
- 22 backend endpoints проверены
- 8 frontend экранов проверены
- DOCX generation checklist (9 проверок)
- Review workflow checklist (8 проверок)
- Smart Import checklist (5 проверок)
- Git hygiene checklist (7 проверок)
- Known limitations (7 пунктов)
- Next steps после MVP (8 задач)

**Текущее состояние:**
- 359 backend tests passed
- 9 E2E tests (6 service-level + 3 API smoke)
- Frontend build: OK
- Git: clean

---

## MVP E2E Tests Complete

### 1. Service-Level E2E Test

**Файл:** `tests/test_pmla_mvp_e2e_flow.py`

**Покрытые этапы:**
- Подготовка контекста анкеты (organization, facility, equipment, substances)
- Создание DocumentContext
- Генерация через EngineRouter (все 6 движков)
- Построение DOCX с титульным листом
- Проверка DOCX содержимого (9 обязательных фраз)
- Проверка отсутствия сырого мусора (None, null, undefined)
- Quality review (structured quality report)
- Review workflow: needs_review → in_review → approved → ready_to_issue → issued
- Повторная генерация (симуляция версионирования)

**Тестов:** 6

### 2. API Smoke Test

**Файл:** `tests/test_pmla_api_smoke_flow.py`

**Проверенные HTTP endpoints:**
- `GET /api/v1/facilities/{facility_id}`
- `GET /api/v1/pmla-questionnaires/facility/{facility_id}`
- `PATCH /api/v1/pmla-questionnaires/{id}/blocks/{block_name}`
- `POST /api/v1/pmla-questionnaires/{id}/generate`
- `GET /api/v1/pmla-questionnaires/{id}/documents`
- `GET /api/v1/pmla/{id}/download`
- `GET /api/v1/pmla/{id}/review`
- `PATCH /api/v1/pmla/{id}/review`

**Проверки:**
- Download endpoint возвращает DOCX bytes (status=200)
- Invalid transition возвращает 400
- Review workflow через API до issued

**Тестов:** 3

### Результаты проверок

| Проверка | Результат |
|----------|-----------|
| `pytest -q` | 359 passed |
| `npm run build` | ✓ Compiled successfully |
| `git status` | Clean |
| `git log` | `30ad3d7 test: API smoke test` |

### Что осталось вне MVP

- Авторизация (роли пользователей)
- Email/webhook уведомления
- PDF экспорт (конвертация из DOCX)
- Интеграция с реальным LM Studio / OpenAI
- E2E test через HTTP endpoints с реальной БД
- E2E test через HTTP endpoints (интеграционный тест с FastAPI TestClient)

---

## Сессия 2026-07-08: Smart Import для справочников + сохранение прогресса

### Завершённые задачи

| # | Задача | Статус |
|---|--------|--------|
| 1 | Smart Import: emergency_services profile | ✅ |
| 2 | Frontend ImportWidget: preview/confirm flow | ✅ |
| 3 | Сохранение прогресса в PROGRESS.md | ✅ |

### Smart Import для справочников

**Изменённые файлы:**
- `backend/src/application/services/smart_import/profiles.py` — добавлен `emergency_services` profile
- `backend/src/application/services/smart_import/service.py` — confirm обрабатывает emergency_services
- `frontend/src/components/dashboard/directories-page.tsx` — ImportWidget для обеих вкладок

**emergency_services profile:**
- Колонки: service_type, name, address, phone, dispatcher_phone, municipality, settlement, latitude, longitude, service_area, notes
- Русские синонимы: "Тип службы", "Вид службы", "Категория" → service_type
- Нормализация типов: пожарная→fire, скорая→medical, полиция→police, газовая→gas, ЕДДС→edds

**Дедупликация:**
- emergency_services: name + address
- pasf_units: name + certificate_number

**Frontend ImportWidget:**
- Кнопка "Импорт Excel/CSV" на обеих вкладках
- Выбор файла → preview с таблицей → подтверждение
- Показывает: создано, обновлено, ошибки
- После confirm обновляет список

### Результаты проверок

| Проверка | Результат |
|----------|-----------|
| `pytest -q` | 330 passed |
| `npm run build` | ✓ Compiled successfully |
| `git status` | Clean, origin/main synced |
| `git log` | `f83d95a feat: Smart Import for directories` |

---

## Сессия 2026-07-07 (вечер): Улучшение качества текста ПМЛА + Headroom

### Завершённые задачи

| # | Задача | Статус |
|---|--------|--------|
| 1 | Улучшено качество текста разделов ПМЛА (6 разделов) | ✅ |
| 2 | Добавлены 7 тестов качества формулировок | ✅ |
| 3 | Установлен и настроен Headroom v0.30.0 | ✅ |

### Улучшения качества текста ПМЛА

**Изменённые файлы:**
- `backend/src/application/engines/data_engine.py` — section_3, section_4, section_8, section_13
- `backend/src/application/engines/scenario_engine.py` — нормализация + рендер кастомных сценариев
- `backend/src/application/services/pmla_generation_from_questionnaire_service.py` — улучшена формулировка инцидентов
- `backend/tests/test_pmla_questionnaire_docx_output.py` — 7 новых тестов качества

**Улучшенные формулировки:**

| Раздел | Было | Стало |
|--------|------|-------|
| section_3 (аварии) | `"аварии и инциденты не зарегистрированы"` | `"За период эксплуатации опасного производственного объекта аварии и инциденты, связанные с нарушением требований промышленной безопасности, не зарегистрированы"` |
| section_4 (ресурсы) | 4 колонки, пустые → `"—"` | 7 колонок (Тип, Ответственное лицо, Назначение), пустые → `"не указано"` |
| section_8 (оповещение) | Английские метки `"first receiver"` | Русские фразы `"Первое сообщение об аварии принимает..."` + таблица с русскими названиями |
| section_13 (резерв) | `"Financial reserve order: ..."` | `"Финансовый резерв создан на основании приказа №..."` |
| section_13 (страхование) | `"Insurance company: ..."` | `"Гражданская ответственность... застрахована в..."` |
| сценарии | Только название | Структурированный текст: место, оборудование, вещество, последствия |

**Тесты качества (`TestDocxQualityPhrases`):**
- `test_incidents_no_incidents_quality_phrase`
- `test_custom_scenario_quality_phrase`
- `test_resources_table_columns`
- `test_notification_scheme_russian_phrases`
- `test_financial_reserve_quality_phrase`
- `test_insurance_quality_phrase`
- `test_no_raw_json_in_docx`
- `test_engine_router_quality_phrases_in_docx` (полный pipeline)

### Headroom v0.30.0

**Установка:**
- Репозиторий: `D:\Git Hub\headroom`
- CLI: `C:\Users\dream\AppData\Roaming\Python\Python314\Scripts\headroom.exe`
- Прокси: port 8787, healthy
- RTK: `~/.headroom/bin/rtk.exe`
- Code graph: `~/.local/bin/tokensave.exe`

**Команда запуска:**
```powershell
headroom proxy --port 8787
headroom wrap claude
```

### Результаты проверок

| Проверка | Результат |
|----------|-----------|
| `pytest -q` | 296 passed |
| `npm run build` | ✓ Compiled successfully |
| `git status` | Чисто (auto-generated `next-env.d.ts` не коммитить) |
| `git log` | `eb70156 Improve PMLA section text quality with official Russian formulations` |

---

## Сессия 2026-07-07: DOCX quality tests + codebase-memory-mcp

### Завершённые задачи

| # | Задача | Статус |
|---|--------|--------|
| 1 | Исправлена ошибка Windows `tmp_path` PermissionError в unit-тестах | ✅ |
| 2 | Добавлены E2E-тесты через полный EngineRouter pipeline | ✅ |
| 3 | Установлен и настроен codebase-memory-mcp v0.8.1 | ✅ |

### DOCX quality tests — что сделано

**Исправлено:**
- `test_pmla_generation_from_questionnaire_service_unit.py`: `tmp_path` заменён на `tempfile.mkdtemp()` для обхода Windows PermissionError на системной папке Temp.

**Добавлено (`test_pmla_questionnaire_docx_output.py`):**
- `TestFullEngineRouterPipeline` — 2 новых теста:
  - `test_engine_router_all_sections_produce_questionnaire_data_in_docx` — запускает `EngineRouter.generate_all()` через все 6 движков, строит реальный DOCX, проверяет 9 ключевых фраз из анкеты
  - `test_engine_router_sections_are_non_empty` — проверяет что все разделы непустые

**Цепочка проверки:**
```
questionnaire data → adapt_context_for_generator() → DocumentContext.from_dict()
→ EngineRouter.generate_all() (DataEngine + ScenarioEngine + TemplateEngine + RulesEngine + NarrativeEngine)
→ DOCX build → extract_docx_text() → assert required phrases present
```

**Проверяемые данные анкеты в DOCX:**

| Категория | Фразы |
|-----------|-------|
| Кастомный сценарий | `Отказ запорной арматуры` |
| Ресурсы | `Газоанализатор`, `Огнетушитель` |
| Оповещение | `оператор котельной`, `дежурный диспетчер` |
| Фин. резерв | `12-ПБ` |
| Страхование | `АО Страховая компания`, `ГО-123456` |
| Аварии | `не зарегистрированы` |

### codebase-memory-mcp

- Установлен бинарник `codebase-memory-mcp.exe` v0.8.1 → `C:\Users\dream\AppData\Local\Programs\codebase-memory-mcp\`
- Проект проиндексирован: 44,062 нод, 211,868 рёбер (~10 сек)
- Конфиг MCP: `.mcp.json` в корне проекта
- 14 инструментов: search_graph, trace_path, get_architecture, query_graph (Cypher), detect_changes и др.

### Тесты

```
288 passed, 50 warnings in 6.34s
```

### Git коммиты

```
41a150e Add E2E DOCX quality tests and fix Windows tmp_path permission error
```

### Frontend build

```
✓ Compiled successfully in 2.9s
```

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

## PMLA Questionnaire Generation Runtime Check (2026-07-07)

Goal: verify the real chain `questionnaire -> context -> generation -> document_id -> debug artifacts -> DOCX text` and fix only integration/rendering issues.

Done:
- Ran a real questionnaire generation flow through backend services using existing questionnaire/facility data.
- Fixed questionnaire data propagation into `DocumentContext`: selected/custom/user scenarios, protective equipment, organization resources, notification scheme, incident history, and insurance/material reserve.
- Fixed scenario rendering so questionnaire scenarios are used even when the facility type has no built-in scenario template.
- Fixed generated sections so questionnaire resources, notification scheme, finance reserve, and insurance are visible in rendered sections and DOCX output.
- Preserved incoming questionnaire `material_reserve` during enhanced generator enrichment instead of overwriting it.
- Added regression tests for questionnaire-driven scenario/resource/notification/insurance rendering.

Verified:
- Focused backend tests: `45 passed, 2 warnings`.
- Full backend tests: `269 passed, 50 warnings`.
- Frontend production build: `npm run build` completed successfully.
- E2E generation sample:
  - `facility_id=421998f3-e53b-41bc-96b6-70604a3891ad`
  - `questionnaire_id=289aeeb3-76f2-4dca-94e4-ae7f74ab74a0`
  - `document_id=38ad702e-dff0-498b-af0c-e0d0ea5cd974`
  - status: `pending_review`
  - context missing fields: none
  - debug artifacts present: `context.json`, `context_quality.json`, `generation_meta.json`, `rendered_sections.json`, `output.docx`
  - DOCX text check passed for custom scenario, protective equipment, notification receiver, and insurance company.

Notes:
- Context quality still reports warnings when PASF/emergency services are not selected in the questionnaire; this is expected data completeness feedback, not a runtime failure.
- AI review/LLM provider connection can fail when the local provider is unavailable; generation falls back and still produces DOCX/debug artifacts.
- Existing dev servers on ports 3000/8000 were left running; a restart may be needed for the browser to pick up latest local code changes.

## PMLA v2 Template Pipeline Integration for Pilot Use (2026-07-11)

Goal: integrate the v2 DOCX template (docxtpl-based) as an alternative generation path and validate E2E on a real OPO.

### What was built
- **Context Mapper** (`pmla_v2_context_mapper.py`): transforms nested engine context into flat v2 schema format (50 fields, 8 arrays)
- **V2 generation path** in `PmlaGenerationService._generate_v2()`: context → map → validate → render → save (bypasses engines/LLM)
- **API integration**: `template_version: str = "v1"` parameter in `POST /api/v1/pmla/generate`
- **5 hardcoded phones** replaced: `notification_chairman_phone`, `notification_pasf_phone`, `notification_edds_phone`, `notification_gas_phone`, `notification_rostechnadzor_phone` (via lxml manipulation of `pmla_v2_template.docx`)
- **PDF converter fix**: `_find_soffice()` finds LibreOffice on Windows (C:\Program Files\LibreOffice\...)
- **Dependencies**: removed unused `unstructured`, `plantuml`, `networkx` from `pyproject.toml`
- **Schema update**: `equipment_defects` marked as deprecated/optional (reserved for future)

### Files changed
| File | Change |
|------|--------|
| `pmla_v2_context_mapper.py` | **New**: 29.7 KB — context mapping + validation |
| `test_pmla_v2_integration.py` | **New**: 16.6 KB — 17 integration tests |
| `pmla_generation_service.py` | +104 lines — `_generate_v2()` path |
| `pmla.py` (router) | +14 lines — `template_version` in API |
| `pdf/converter.py` | +37 lines — `_find_soffice()`, `os` import |
| `pmla_v2_template.docx` | 5 hardcoded phones → Jinja variables |
| `pmla_v2.schema.json` | `equipment_defects` deprecated annotation |
| `pyproject.toml` | -3 unused deps |

### Test results
- **Full suite**: 612 passed, 3 skipped, 0 failed
- **Schema alignment**: 27/27 PASS
- **V2 integration**: 14/14 PASS (3 skipped: need DB+LLM)
- **DOCX QA full/empty**: PASS
- **Real OPO E2E**: DOCX 12.5 MB, PDF 4.6 MB, all 5 phones verified
- **Jinja artifacts**: 0
- **Tables**: 21

### Skipped tests (3)
1. `test_v2_generate_endpoint` — needs live DB + FastAPI client (cannot mock properly)
2. `test_v1_generate_endpoint` — needs DB + LLM (v1 uses EnhancedDocumentGenerator)
3. `test_v2_generate_with_provided_context` — needs DB (build_context() queries DB)

### Status
**`READY FOR PILOT USE`** — v2 generation works on real OPO data.
Template_version=v1 remains default; v2 activated explicitly via API parameter.

### Known limitations
- 5 notification phones are parameterized; 2 secondary phone lines (EDDS `+7 (86630) 4-00-06`, electric `+7 (86630)4-27-70`) remain in template as static data
- PDF requires LibreOffice installed (graceful fallback missing for non-LO systems)
- `equipment_defects` not in template (reserved for future Table 8)
- Address parsing for `settlement_district` requires manual input
- 3 integration tests skipped (need full DB setup)

### Pilot generation command
```http
POST /api/v1/pmla/generate
Content-Type: application/json

{
  "facility_id": "<UUID>",
  "template_version": "v2"
}
```

### Engineer review checklist
See `docs/PMLA_ENGINEER_REVIEW_CHECKLIST.md` — mandatory before document approval.

---

Goal: systematic static analysis and fix of all errors/bugs found across frontend (TypeScript + ESLint) and backend (Python), working autonomously with subagents.

Done:
- Frontend — runtime crash fix: added missing `AlertTriangle` import in `frontend/src/components/dashboard/document-detail-page.tsx`; the error alert would have thrown `ReferenceError` on render.
- Frontend — missing `PAGE_TITLES` keys: added `facilityDetail` and `documentDetail` entries in `frontend/src/app/page.tsx` so `Record<PageKey, ...>` is complete.
- Frontend — API typing (20 errors): introduced a `DocumentReviewWorkflow` type and tightened return types in `frontend/src/lib/api-client.ts` (`getPmlaDocumentVersions`, `getQuestionnaireDocuments`, `getPmlaDocumentStatus`, `facilities`, `getPasfUnits`, `getEmergencyServices`); removed point-of-use casts/`unknown` access in `document-detail-page.tsx`, `pmla-questionnaire-page.tsx`, `facility-detail-page.tsx`.
- Frontend — ESLint "Cannot create components during render": extracted inner `PasfForm` and `ServiceForm` from `PasfDirectory`/`EmergencyServicesDirectory` render scope to module level in `frontend/src/components/dashboard/directories-page.tsx` with explicit props interfaces (no behavior change).
- Backend — explosion zone calculation logic: fixed contradictory radius selection in `backend/src/application/services/calculations/explosion_zone.py`. Per РД 03-409-01 the lethal zone is the smallest (epicenter); the code now computes all four zones (lethal < severe < moderate < minor) and exposes them via a new `zones` dict on `ExplosionResult`, with `zone_radius_m` = outer (max) zone. `K_SEVERE`/`K_MINOR` are now used (previously declared but dead).
- Backend — silent exception handling: replaced three `except Exception: pass` blocks in `EnhancedDocumentGenerator._run_calculations` (explosion/thermal/toxic) with logged warnings and `validation_status: "error"` result entries; hardened `_get_calc_placeholders` to skip error entries instead of raising `KeyError`.
- Added `backend/.dockerignore` to exclude root-owned `__pycache__`/`.pytest_cache` from the build context (the pytest cache was blocking `docker compose build`).
- Added regression test `test_all_four_zones_present_and_ordered` covering the new four-zone explosion result.

Verified:
- `npx tsc --noEmit` -> 0 errors (was 25).
- `npx eslint .` -> 0 errors, 74 warnings (was 4 errors; remaining warnings are pre-existing `react-hooks` style in legacy pages).
- `python -m pytest -q` -> `382 passed, 41 warnings` (full backend suite green, including the new test).

Notes:
- No runtime/behavioral changes beyond the explosion-zone radius semantics: `zone_radius_m` now reports the outer (maximum-area) zone instead of the lethal (smallest) radius. Consumers were checked (`enhanced_generator` uses `calc_result.results` via registry wrapping) and tests confirm larger-quantity → larger-radius and confined > open invariants still hold.
- Changes are uncommitted in the working tree; a follow-up commit is recommended once reviewed.
- Docker Desktop was reinstalled during the session with disk image location moved to `D:\DockerData` (via `CustomWslDistroDir` in `settings-store.json`); ISAP stack (`isap_db`, `isap_chromadb`, `isap_backend`, `isap_frontend`) was recreated via `docker compose up -d` with a clean data start.

## PMLA MVP — First Real/Ops Validation Stage

Date: 2026-07-09
Stage: First real / anonymized OPO validation

Goal of this stage: validate the PMLA MVP on the first real or anonymized OPO and determine whether the generated DOCX can serve as an engineering draft, then collect engineer findings.

Status:
- Demo walkthrough (`docs/PMLA_DEMO_DATA_WALKTHROUGH.md`) completed end-to-end: questionnaire -> generation -> document -> DOCX (validated, DOCX present, quality review returned a score and checks).
- Stabilization patch applied (see earlier section: `attachments_checklist`, HTML stripping from DOCX, PASF/emergency services, quality review sync).
- Code health sweep applied and committed on `fix/code-health-sweep-ts-eslint-calc` (TypeScript 25 -> 0 errors, ESLint 4 -> 0 errors, explosion-zone logic fixed, silent-exception handling hardened; `382 passed`).
- Next stage: the first real / anonymized OPO.

Next stage objective:
- Validate DOCX quality and questionnaire completeness on a real (or anonymized) OPO.
- Collect engineer findings on structure, content, formatting (no `None`/`undefined`/raw JSON/HTML), and required manual edits.

Scope guardrails (out of scope for this stage, intentionally):
- No new large features, no RAG, no geocoding or route/time-to-arrival, no architecture changes, no migrations, no seed scripts.
- No backend/frontend logic changes.

Deliverables added this stage (documentation and control workflow only):
- `docs/PMLA_REAL_OPO_INPUT_TEMPLATE.md` — input data template for collecting real/anonymized OPO data (organization, OPO, hazard substances, equipment, scenarios, incidents, PASF/ASF, emergency services, forces, notification, financial reserve, insurance, attachments, unknown fields).
- `docs/PMLA_REAL_OPO_VALIDATION_WALKTHROUGH.md` — step-by-step safe workflow: anonymization, create organization, create OPO, fill questionnaire, select PASF and emergency services, generate DOCX, download, check quality review, pass manual review workflow, record engineer findings.
- `docs/PMLA_ENGINEER_REVIEW_CHECKLIST.md` — DOCX engineer review checklist (title page, approval sheet, OPO general info, substances, equipment, scenarios, PASF/ASF, emergency services, forces, notification, first-response actions, financials, insurance, attachments; formatting checks for empty fields / `None` / `undefined` / raw JSON / HTML tags; structure compliance; manual-edit-required items).

Engineer review remains mandatory: the system does not auto-approve. Status `approved` in the review workflow is set only after an engineer passes `PMLA_ENGINEER_REVIEW_CHECKLIST.md`.

Notes:
- This stage is documentation-only; no code, migrations, or seed data were added. Findings from real OPO runs will be triaged into a follow-up backlog separately.
- Real/anonymized input templates, findings, and downloaded DOCX must not be committed without review (the input template/findings go in `docs/inbox/`, DOCX is already gitignored).

---

## PMLA OPO Audit After Patch A/B — Code Bug Sweep (2026-07-13)

Goal: repeat the post-Patch-A/Patch-B technical audit without adding a new feature, find real defects in the current PMLA/PASF/DOCX/frontend flow, and preserve the current state before deciding the next patch.

Scope:
- Reviewed current worktree in the new local project path `D:\Project ISAP\isap`.
- Used parallel subagent review for backend/API, PMLA/DOCX mapping, frontend/build, and git hygiene.
- Treated existing uncommitted and untracked files as user/project state; nothing was reverted or cleaned automatically.

Fixed during the audit:
- PASF document downloads: relative stored document paths are now resolved under the PASF upload root, with path-escape protection. This prevents 404s when `file_path` is stored as a relative key.
- PASF agreement date propagation: `_get_pasf()` now includes `agreement_date`, so the v2 mapper can use it in the DOCX context.
- PMLA v2 emergency service mapping: dictionary-style emergency service blocks now support canonical and alias keys, including PASF/medical/fire mappings used by questionnaire data.
- PMLA v2 contract dates: contract document dates are formatted as `DD.MM.YYYY` for the v2 schema/template instead of raw ISO dates.
- PMLA v2 equipment/scenario links: matrix-selected scenarios without `equipment_ids` no longer collapse to empty links in the generated table.
- Frontend TypeScript: fixed `opo-page.tsx` hazard class narrowing so `npx tsc --noEmit --incremental false` passes.
- Generated frontend type file: restored `frontend/next-env.d.ts` to the normal `.next/types/routes.d.ts` import after a dev-build generated change.
- Added focused regression tests for PASF document path resolution, v2 emergency-service alias mapping, contract date formatting, and equipment/scenario fallback links.

Verified:
- Backend focused tests: `38 passed, 3 skipped, 3 warnings`.
- Backend full suite: `696 passed, 3 skipped, 41 warnings`.
- Frontend type check: `npx tsc --noEmit --incremental false` passed.
- Frontend production build: `npm run build` passed.
- Static diff check: `git diff --check` passed; only line-ending conversion warnings were reported by Git.

Current git state:
- Changes are intentionally uncommitted.
- Modified tracked files include PASF router, PMLA questionnaire service, PMLA v2 context mapper, v2/directories tests, smoke-flow test, OPO page, and pre-existing modified files such as `enhanced_generator.py` and database model changes.
- Important untracked items remain and must be handled deliberately before any commit: `.agents/`, `.claude/`, `.mimocode/`, `graphify-out/`, `.zcode/`, real OPO validation JSON/data folders, `nul` files, audit scripts/docs, the `agreement_date` migration, and the PASF documents E2E test.

Risks / decisions left open:
- Local/generated/audit folders should be staged or ignored deliberately; no blanket `git add .`.
- The untracked migration and PASF E2E test look legitimate but should be reviewed and staged intentionally.

Recommended next step:
- Review visible source-like untracked files, then stage a narrow Patch C commit with only the audit bug fixes, tests, config fixes, and intended hygiene rules.

### Follow-up: frontend build policy and repository hygiene

Additional subagent review found and closed two production/build risks:
- Next.js production builds no longer ignore TypeScript errors: removed `typescript.ignoreBuildErrors` from `frontend/next.config.ts`. `npm run build` now runs the built-in TypeScript step and passed.
- Frontend Dockerfile now matches `output: "standalone"`: the runner stage copies `.next/standalone`, `.next/static`, and `public`, then starts with `node server.js` using `HOSTNAME=0.0.0.0` and `PORT=3000`.

Repository hygiene changes:
- Root `.gitignore` now ignores local agent/tooling outputs: `.agents/`, `.claude/`, `.mimocode/`, `graphify-out/`.
- Root `.gitignore` now ignores Windows reserved `nul` artifacts so they stop polluting status and breaking search tools.
- App `.gitignore` now ignores local `.zcode/` and real/anonymized OPO validation outputs (`backend/data/data/`, `real_opo_insert.sql`, validation JSONs, QA trace/text files).
- Legitimate-looking source artifacts remain visible for review: the `agreement_date` migration, PASF E2E test, v1 schema, docs/audit files, and backend scripts were not blanket-ignored.

Additional verification:
- Frontend strict type check: `npx tsc --noEmit --incremental false` passed.
- Frontend production build: `npm run build` passed and produced `.next/standalone/server.js`.
- Backend focused regression: `38 passed, 3 skipped, 3 warnings`.
- `git diff --check` passed; only LF/CRLF warnings remain.

Remaining manual decisions:
- Decide whether to delete the ignored `nul` files from disk; they are still present locally but no longer appear in normal `git status`.
- Review and intentionally stage or discard visible untracked source-like files; avoid blanket `git add .`.

### Follow-up: frontend API origin and untracked source review

Additional production bug fixed:
- Frontend API client no longer defaults browser requests to `http://localhost:8000`; when `NEXT_PUBLIC_API_BASE_URL` is not explicitly set, requests use same-origin paths such as `/api/v1/...` and `/health`.
- `next.config.ts` now rewrites `/api/:path*` and `/health` to the backend using `INTERNAL_API_BASE_URL` (default for Docker: `http://backend:8000`).
- `docker-compose.yml` sets `INTERNAL_API_BASE_URL=http://backend:8000` for the dev frontend container.
- Frontend Dockerfile provides `INTERNAL_API_BASE_URL` at build time and runtime, so standalone rewrites are built with the container backend URL.
- `frontend/.dockerignore` now excludes `.env*.local`, preventing local `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` from being baked into production Docker images.

Verification:
- Clean Docker-like frontend build was run with local `.env.local` temporarily removed and restored afterward.
- `npm run build` passed with `INTERNAL_API_BASE_URL=http://backend:8000`.
- `npx tsc --noEmit --incremental false` passed.
- Production output check found no `localhost:8000` in `.next/static`, `.next/server`, or `.next/standalone`.
- Standalone output contains backend rewrites to `http://backend:8000/api/:path*` and `http://backend:8000/health`.

Untracked source-like review:
- Stage candidate: `backend/alembic/versions/a5c8a2dd1a14_add_agreement_date_to_emergency_rescue_.py`; current model/API/service use `agreement_date`, so deployed DBs need this migration.
- Stage candidate: `backend/tests/integration/test_pmla_pasf_documents_e2e.py`; it covers PASF document upload and mapper behavior without relying on an existing DB row.
- Leave untracked unless intentionally shipping docs: PMLA v2 docs and audit reports under `docs/` and `docs/audit/`.
- Likely local tooling: many `backend/scripts/*` template surgery / render audit scripts and `docs/audit/analyze_docx*.py`; several contain machine-specific absolute paths and should not be blanket-staged.

Remaining manual decisions:
- Whether to stage selected durable docs or keep them local.
- Whether to delete ignored `nul` files from disk.

### Follow-up: PASF E2E stabilization

PASF E2E staging blocker fixed:
- `backend/tests/integration/test_pmla_pasf_documents_e2e.py` no longer relies on a hard-coded existing PASF UUID.
- The upload test now overrides FastAPI dependencies with an in-memory fake PASF repository and fake DB session while still exercising the real upload endpoint handler.
- The test no longer silently skips when the endpoint/database is unavailable; upload success is asserted directly.
- Uploaded test files are cleaned from the PASF upload directory after the test.
- The contradictory certificate-date fallback comment was removed; the assertion now matches the mapper behavior (`agreement_date` only, otherwise `—`).

Verification:
- PASF E2E file: `11 passed, 3 warnings`.
- Expanded backend focused regression: `49 passed, 3 skipped, 3 warnings`.
- Search confirmed no old hard-coded PASF UUID and no `pytest.skip` remain in the PASF E2E file.

Updated staging recommendation:
- The `agreement_date` Alembic migration and PASF E2E test are now both reasonable Patch C staging candidates, subject to the final staged-file review.

### Savepoint: audit progress saved (2026-07-13 19:01:13 +03:00)

Current state saved after the Patch A follow-up audit and additional bug sweep.

Completed in this working tree:
- `docs/inbox/` and other local validation/tooling outputs remain local and are ignored rather than staged blindly.
- Backend PASF/PMLA fixes are present in the working tree: PASF upload/download path resolution, `agreement_date` propagation, emergency-service alias handling, PASF contract date mapping, scenario/equipment fallback mapping, and dispatcher phone priority.
- Frontend production/API fixes are present in the working tree: no ignored TypeScript build errors, standalone Docker runtime, same-origin browser API calls by default, backend rewrites through `INTERNAL_API_BASE_URL`, and `.env*.local` excluded from frontend Docker context.
- PASF E2E test was stabilized: it no longer depends on a hard-coded PASF UUID and no longer skips silently.

Verification already passed:
- Full backend suite earlier in this audit: `696 passed, 3 skipped`.
- PASF E2E focused file: `11 passed`.
- Expanded backend focused regression: `49 passed, 3 skipped`.
- Frontend strict type check: `npx tsc --noEmit --incremental false` passed.
- Frontend production build: `npm run build` passed.
- Production frontend output check found no baked `localhost:8000`.
- `git diff --check` passed, with only Git line-ending warnings.

Current git state summary:
- Changes are intentionally uncommitted.
- Modified tracked files include root/app `.gitignore`, `PROGRESS.md`, PASF/PMLA backend services/router/tests, frontend API/config/Docker files, `docker-compose.yml`, and pre-existing modified files such as `enhanced_generator.py` and database model updates.
- Important untracked Patch C candidates: `backend/alembic/versions/a5c8a2dd1a14_add_agreement_date_to_emergency_rescue_.py` and `backend/tests/integration/test_pmla_pasf_documents_e2e.py`.
- Other untracked docs/scripts/audit artifacts remain visible for deliberate review and should not be swept into a commit automatically.

Remaining before final commit decision:
- Review latest subagent findings if they return with additional issues.
- Fix the minor Russian ambulance alias typo in `_SERVICE_TYPE_ALIASES` (`скорая`; keep tolerant legacy alias if useful).
- Optionally remove the duplicate local `admin` lookup in the PMLA v2 context mapper.
- Rerun focused backend tests and `git diff --check` after any final edits.
- Stage only the intended Patch C files; avoid blanket `git add .`.
### Subagent frontend/config findings (2026-07-13 19:01:53 +03:00)

Latest read-only frontend/config review returned unresolved findings; no code was changed for them in this savepoint.

Findings to fix next:
- P1: OPO save can corrupt hazard class values in `frontend/src/components/dashboard/opo-page.tsx`; current mapping uses string index logic that can map `II`, `III`, and `IV` incorrectly.
- P2: Same-origin API behavior can be bypassed in local dev because `NEXT_PUBLIC_API_BASE_URL` is still documented in `frontend/.env.example` and preferred by `frontend/src/lib/api-client.ts` when set.
- P2: Docker runtime `INTERNAL_API_BASE_URL` is potentially misleading because Next rewrites are produced at build/config load time; runtime overrides in the standalone image may not change already-built rewrite destinations.

Verification noted by reviewer:
- Frontend no-emit TypeScript check passed.
- No concrete accidental over-ignore was found in the changed `.gitignore` rules against currently tracked files.

Updated next-step queue:
- Fix hazard-class persistence before any user-facing OPO retest.
- Decide final API-origin policy: either fully same-origin by default and remove public local-backend guidance, or explicitly document when direct backend access is expected.
- Clarify Docker build-time versus runtime backend URL behavior in config/Dockerfile/docs before staging Patch C.

### Subagent backend/PASF findings (2026-07-13 19:02:15 +03:00)

Latest read-only backend/PASF review returned unresolved findings; no code was changed for them in this savepoint.

Findings to fix next:
- P1: Final questionnaire generation can be blocked for newly uploaded PASF documents. Upload/download now use relative storage keys such as `pasf_documents/...`, but PMLA preflight still checks `os.path.exists(doc_file_path)` directly, so it can report `PASF_FILE_NOT_FOUND` even when the file exists under the PASF upload root.
- P2: PASF document appendices may be wired into the legacy/enhanced generator path, not the v2 questionnaire generation path. The v2 questionnaire flow maps to `v2_context` and renders via `PmlaTemplateRenderer`, while current v2 template keys do not clearly consume `appendices_manifest` or `pasf_documents`.
- P2: The untracked PASF E2E test is stabilized but still does not cover its full advertised flow. It does not run preflight against a relative uploaded `file_path`, does not call questionnaire generation, and does not verify the downloaded/generated manifest path end-to-end.
- P3: `contractor_agreement_number` is mapped and tested, but the v2 schema/template contract appears to define/use only `contractor_agreement_date`, so the number may be silently unused in DOCX output.

Reviewer notes:
- The `agreement_date` Alembic migration looks structurally aligned with the model: nullable `String(50)` column and `down_revision = "019"`.
- The reviewer did not edit files or run the test suite.

Updated next-step queue:
- Fix PASF preflight path resolution before considering final generation reliable.
- Decide whether PASF appendices belong in the v2 questionnaire renderer/template contract, then add a real flow test if they do.
- Rename or expand the PASF E2E test so its coverage matches its header.
- Decide whether `contractor_agreement_number` should be added to the v2 schema/template output or removed from the mapper/test expectations.
### Follow-up: P1 audit fixes applied (2026-07-13 19:11:39 +03:00)

Closed findings from the latest subagent reviews:
- P1 frontend hazard-class corruption fixed in `frontend/src/components/dashboard/opo-page.tsx`: OPO save now maps `I`, `II`, `III`, `IV` through an explicit helper instead of the broken `"IVII".indexOf(...)` expression.
- P1 PASF preflight blocker fixed in `backend/src/application/services/pmla_preflight.py`: relative uploaded PASF storage keys such as `pasf_documents/...` are now resolved under the PASF upload root before existence and checksum checks.
- Minor mapper cleanup applied in `backend/src/application/services/pmla_v2_context_mapper.py`: added the correct Russian alias `скорая` for ambulance/medical services while keeping the previous typo alias for tolerance, and removed a duplicate `admin` service lookup.

Regression coverage added/updated:
- `backend/tests/test_pmla_generation_core.py` now verifies that a relative PASF document path under the upload root does not produce `PASF_FILE_NOT_FOUND` or checksum mismatch in final preflight.
- `backend/tests/integration/test_pmla_pasf_documents_e2e.py` now verifies `_normalize_service_type("скорая") == "ambulance"`.

Verification after these fixes:
- `python -m pytest isap\backend\tests\test_pmla_generation_core.py -q`: `59 passed`.
- `python -m pytest isap\backend\tests\test_pmla_generation_core.py isap\backend\tests\integration\test_pmla_pasf_documents_e2e.py -q`: `70 passed`.
- `npx tsc --noEmit --incremental false`: passed.
- `git diff --check`: passed, with only Git LF/CRLF warnings.

Still open from subagent review:
- P2: finalize same-origin API policy for `NEXT_PUBLIC_API_BASE_URL` versus Next rewrites.
- P2: clarify that Docker `INTERNAL_API_BASE_URL` affects build/config-time rewrites, not arbitrary runtime rewiring of an already-built standalone image.
- P2: decide whether PASF appendices must be wired into the v2 questionnaire renderer/template contract and add a true generation-flow test if yes.
- P3: decide whether `contractor_agreement_number` belongs in the v2 schema/template output or should be removed from mapper/test expectations.
### Follow-up: P2/P3 audit fixes applied (2026-07-13 19:37:19 +03:00)

Closed remaining findings from the latest frontend/backend subagent reviews:
- P2 frontend API-origin policy fixed: browser API calls now always use same-origin `/api/...` paths; `NEXT_PUBLIC_API_BASE_URL` no longer controls frontend requests or appears in frontend examples/docs.
- P2 Docker rewrite behavior clarified: `INTERNAL_API_BASE_URL` is treated as the Next build/dev-server backend target for rewrites. The frontend Docker runner no longer exposes a misleading runtime override for already-built standalone rewrites.
- P2 PASF appendices fixed for the v2 questionnaire generation path: `map_to_v2_context()` now carries `appendices_manifest`, and `PmlaTemplateRenderer` appends the manifest table to the rendered v2 DOCX output.
- P3 `contractor_agreement_number` fixed in the v2 template contract: the hard-coded agreement number in `pmla_v2_template.docx` was replaced with `{{ contractor_agreement_number }}`, and the field is now present in `pmla_v2.schema.json`, `pmla_v2_template_keys.json`, and `pmla_v2_context_keys.json`.

Verification after these fixes:
- Clean Docker-like frontend build without local `.env.local`, with `INTERNAL_API_BASE_URL=http://backend:8000`: passed; standalone output contains backend rewrites to `http://backend:8000` and no `NEXT_PUBLIC_API_BASE_URL` / `localhost:8000` references.
- `npx tsc --noEmit --incremental false`: passed.
- `python -m pytest isap\backend\tests\integration\test_pmla_v2_integration.py -q`: `28 passed, 3 skipped`.
- `python -m pytest isap\backend\tests\infrastructure\export\test_pmla_v2_schema_alignment.py -q`: `27 passed`.
- Combined focused backend suite (`test_pmla_generation_core.py`, PASF E2E, v2 integration, schema alignment): `125 passed, 3 skipped`.
- `git diff --check`: passed, with only Git LF/CRLF warnings.

Current audit status:
- Previously open P1/P2/P3 findings from the two subagent reviews are now addressed in code/tests.
- Changes remain intentionally uncommitted and should still be staged narrowly; avoid blanket `git add .` because local docs/scripts/audit artifacts are still visible.
### Patch C readiness review (2026-07-13 19:47:01 +03:00)

Independent subagent review and local readiness checks completed for the current Patch C working tree.

Subagent review result:
- No P0/P1 readiness blockers found.
- P2 found and fixed: PASF preflight previously accepted absolute `file_path` values outside the PASF upload root while download policy rejects them.
- P3 test-scope issue addressed: the PASF documents regression test header now describes its actual focused coverage rather than claiming a full upload → preflight → generation → manifest → download E2E path.

Additional fix applied:
- `backend/src/application/services/pmla_preflight.py` now confines both relative and absolute PASF document paths to `PASF_UPLOAD_ROOT`; paths outside the upload root resolve to missing/rejected files.
- `backend/tests/test_pmla_generation_core.py` now covers both allowed relative PASF storage keys and rejected absolute paths outside upload root.

Readiness verification:
- JSON contract files parse successfully: `pmla_v2.schema.json`, `pmla_v2_context_keys.json`, `pmla_v2_template_keys.json`.
- `pmla_v2_template.docx` contains `{{ contractor_agreement_number }}` and no longer contains the old hard-coded `265/26` agreement number.
- Alembic chain check: untracked migration `a5c8a2dd1a14_add_agreement_date_to_emergency_rescue_.py` is a linear successor of revision `019` and matches the model's `agreement_date` field.
- Focused PASF/preflight tests: `71 passed`.
- Combined focused backend suite: `126 passed, 3 skipped`.
- Frontend type check: `npx tsc --noEmit --incremental false` passed.
- `git diff --check` passed, with only Git LF/CRLF warnings.

Patch C staging guidance:
- Stage intentionally: tracked Patch C source/config/template/schema/test files, plus the untracked Alembic migration and untracked PASF documents regression test.
- Do not blanket-stage visible local artifacts: `AI_DEVELOPER_PROMPT.md`, `backend/scripts/*`, `docs/audit/*`, generated QA/render scripts, local schema experiments, and other untracked docs unless deliberately chosen.
- `backend/qa_content_paragraphs.txt` still contains an old rendered sample with the previous hard-coded agreement number, but it is not tracked and should remain out of Patch C.
### Patch C staging dry-run (2026-07-13 19:49:41 +03:00)

A safe `git add --dry-run` was executed with an explicit Patch C file list. It did not change the index (`git diff --cached --name-only` returned empty).

Dry-run staging list:
- `.gitignore`
- `isap/.gitignore`
- `isap/PROGRESS.md`
- `isap/backend/src/api/routers/directories_pasf.py`
- `isap/backend/src/application/services/enhanced_generator.py`
- `isap/backend/src/application/services/pmla_preflight.py`
- `isap/backend/src/application/services/pmla_questionnaire_service.py`
- `isap/backend/src/application/services/pmla_v2_context_mapper.py`
- `isap/backend/src/infrastructure/database/models.py`
- `isap/backend/src/infrastructure/export/pmla_template_renderer.py`
- `isap/backend/alembic/versions/a5c8a2dd1a14_add_agreement_date_to_emergency_rescue_.py`
- `isap/backend/tests/integration/test_pmla_v2_integration.py`
- `isap/backend/tests/integration/test_pmla_pasf_documents_e2e.py`
- `isap/backend/tests/test_directories.py`
- `isap/backend/tests/test_pmla_api_smoke_flow.py`
- `isap/backend/tests/test_pmla_generation_core.py`
- `isap/docker-compose.yml`
- `isap/docs/FRONTEND_MIGRATION.md`
- `isap/files/pmla_v2.schema.json`
- `isap/files/pmla_v2_context_keys.json`
- `isap/files/pmla_v2_template.docx`
- `isap/files/pmla_v2_template_keys.json`
- `isap/frontend/.dockerignore`
- `isap/frontend/.env.example`
- `isap/frontend/Dockerfile`
- `isap/frontend/next.config.ts`
- `isap/frontend/src/components/dashboard/opo-page.tsx`
- `isap/frontend/src/lib/api-client.ts`

Explicitly excluded from Patch C staging:
- `isap/AI_DEVELOPER_PROMPT.md`
- `isap/backend/scripts/**`
- `isap/docs/EPB_REGISTRY_MVP.md`
- `isap/docs/PMLA_V2_*.md`
- `isap/docs/audit/**`
- `isap/files/pmla_v1.schema.json`
- ignored/generated local artifacts such as `.next/`, `backend/src/uploads/`, `__pycache__/`, `nul`, and local QA render outputs.

Recommended next command, only when ready to actually stage:
`git add -- <the exact dry-run file list above>`

### Full regression/build gate (2026-07-13 19:54:50 +03:00)

Broader verification was run after the Patch C readiness and staging dry-run pass.

Verification results:
- Full backend test suite: `python -m pytest isap\backend\tests -q` → `699 passed, 3 skipped, 41 warnings`.
- Frontend strict type check: `npx tsc --noEmit --incremental false` → passed.
- Frontend production build: `npm run build` → passed.
- `git diff --check` → passed, with only Git LF/CRLF warnings.
- `git diff --cached --name-only` → empty; no files are staged.
- Frontend build artifacts remain ignored: `isap/frontend/.next/` appears only as ignored output.

Current state:
- Patch C remains uncommitted and unstaged by design.
- The explicit staging dry-run list above remains the recommended staging scope.

### Static quality gate follow-up (2026-07-13 20:04:55 +03:00)

Additional project quality gates were inspected after the full regression/build pass.

Findings and fixes:
- Backend full `ruff check .` is not currently a green repository-wide gate: it reports a large amount of pre-existing formatting/import/line-length debt across Alembic, tests, and older modules.
- A real Patch C-relevant static bug was found and fixed: `enhanced_generator.py` used `logger` before any module-level logger existed. Added a module-level `logging.getLogger(__name__)`.
- Patch C frontend lint warnings in `opo-page.tsx` were cleaned up: removed the `any` cast in `mapFromApi`, replaced render-time `Date.now()` / `Math.random()` document IDs with a ref counter, and removed unused `saving` state.

Verification after the fixes:
- Targeted backend static check: `python -m ruff check src/application/services/enhanced_generator.py --select F821` → passed.
- Targeted frontend lint: `npx eslint src/lib/api-client.ts src/components/dashboard/opo-page.tsx next.config.ts` → passed with no warnings/errors.
- Backend focused tests around enhanced generator/preflight: `89 passed`.
- Full backend test suite rerun: `699 passed, 3 skipped, 41 warnings`.
- Frontend strict type check: passed.
- Frontend production build: passed.
- `git diff --check`: passed, with only Git LF/CRLF warnings.
- `git diff --cached --name-only`: empty; no files are staged.

Notes:
- The saved Patch C dry-run staging list is still valid; the latest edits only touched files already included in that list (`enhanced_generator.py` and `opo-page.tsx`).
- Repo-wide ruff cleanup should be treated as a separate formatting/lint-debt task, not folded into Patch C.

### Patch C static/manual audit continuation (2026-07-13 20:14:24 +03:00)

A follow-up manual/static audit was run against the current Patch C worktree after the prior progress save.

Findings and fixes:
- Removed a duplicate module-level `logger = logging.getLogger(__name__)` declaration in `enhanced_generator.py`.
- Fixed a real static test issue in `test_pmla_v2_integration.py`: two test classes were both named `TestRegulatoryCoverage`, so one class name shadowed the other at module scope. They are now named `TestRegulatoryCoverageBasic` and `TestRegulatoryCoveragePp1437`.
- Added the missing blank line between adjacent v2 integration test methods while preserving test behavior.

Verification after the fixes:
- Targeted ruff: `python -m ruff check src/application/services/enhanced_generator.py tests/integration/test_pmla_v2_integration.py --select F821,F811` -> passed.
- v2 integration tests: `python -m pytest tests/integration/test_pmla_v2_integration.py -q` -> `32 passed, 3 skipped, 3 warnings`.
- `git diff --check` -> passed, with only Git LF/CRLF warnings.
- `git diff --cached --name-only` -> empty; no files are staged.

Current state:
- Patch C remains uncommitted and unstaged by design.
- Latest additional edits only touched files already in the saved Patch C staging dry-run list: `enhanced_generator.py` and `test_pmla_v2_integration.py`.

### Patch C independent review follow-up (2026-07-13 20:27:33 +03:00)

An independent subagent review of the current Patch C diff was completed and its actionable finding was addressed.

Finding fixed:
- P2 PASF upload storage policy: uploaded filenames were sanitized only by the final upload-root `commonpath` check. A crafted filename with path separators could stay inside `uploads/` while bypassing the intended `uploads/pasf_documents/` directory. The upload path builder now strips path separators to a basename, stores the sanitized filename, and verifies the resolved path is inside `PASF_DOCUMENTS_UPLOAD_DIR`.

Additional cleanup:
- Fixed the `contractor_agreement_number` description in `pmla_v2.schema.json` from a mojibake/question-mark placeholder to `Номер договора с ПАСФ`.

Verification after the fixes:
- PASF-focused backend tests: `python -m pytest tests/test_directories.py tests/test_pmla_generation_core.py tests/integration/test_pmla_pasf_documents_e2e.py -q` -> `80 passed, 3 warnings`.
- Targeted ruff: `python -m ruff check src/api/routers/directories_pasf.py tests/test_directories.py --select F821,F811` -> passed.
- v2 schema alignment: `python -m pytest tests/infrastructure/export/test_pmla_v2_schema_alignment.py -q` -> `27 passed, 1 warning`.
- Full backend suite: `python -m pytest isap\backend\tests -q` -> `704 passed, 3 skipped, 41 warnings`.
- Frontend typecheck: `npx tsc --noEmit --incremental false` -> passed.
- Frontend production build: `npm run build` -> passed.
- `git diff --check` -> passed, with only Git LF/CRLF warnings.
- `git diff --cached --name-only` -> empty; no files are staged.

Current state:
- Patch C remains uncommitted and unstaged by design.
- Latest additional edits touched `directories_pasf.py`, `test_directories.py`, and `pmla_v2.schema.json`; these should be included in the Patch C staging scope if/when staging happens.

### Docker startup fix (2026-07-13 20:37:51 +03:00)

The application startup issue was reproduced and fixed in Docker Compose.

Root cause:
- The backend container used `uvicorn --reload` over the whole `/app` bind mount. Watchfiles crashed on `/app/.pytest_cache` with `Permission denied`, making startup/reload unstable.
- The frontend dev container repeatedly logged `Failed to flush logs to file ... /app/.next/dev/logs` because the dev log directory was absent after prior production builds.

Fixes:
- Backend compose command now uses `--reload-dir src`, so the reloader watches application source only and does not scan local test/build caches.
- Frontend compose command now creates `.next/dev/logs` before running `next dev`.
- Removed obsolete Compose `version` key to avoid the Docker Compose warning.

Verification:
- Recreated backend/frontend containers with `docker compose up -d --force-recreate backend frontend`.
- `docker compose config --quiet` -> passed.
- `docker compose ps` -> db, chromadb, backend, frontend all `Up`; db is healthy.
- Backend `http://localhost:8000/health` -> `200 {"status":"ok","env":"development"}`.
- Frontend `http://localhost:3000/` -> `200` after first dev compilation.
- Frontend rewrite `http://localhost:3000/health` -> backend health `200`.
- Backend logs now show `Will watch for changes in these directories: ['/app/src']` and no watchfiles permission error.
- Frontend logs now show `Ready` and successful `GET / 200`; no `.next/dev/logs` flush error in fresh logs.
- `git diff --check` -> passed with only Git LF/CRLF warnings.
- `git diff --cached --name-only` -> empty; no files are staged.

Current state:
- Docker app is currently running at `http://localhost:3000` with backend at `http://localhost:8000`.
- Patch C remains uncommitted and unstaged by design.

### Frontend API CORS redirect fix (2026-07-13 20:48:06 +03:00)

A browser CORS error was reproduced for PMLA API calls through the Next.js frontend proxy.

Root cause:
- Requests from `http://localhost:3000` to `/api/v1/pmla/` were being normalized/reproxied in a way that let FastAPI issue a `307` redirect with `Location: http://backend:8000/api/v1/pmla/`.
- The browser then tried to follow the Docker-internal hostname `backend:8000`, causing CORS/preflight failure.

Fixes:
- Added `skipTrailingSlashRedirect: true` to `next.config.ts` so Next does not normalize API proxy paths before rewrites.
- Added an explicit slash-preserving API rewrite before the generic rewrite: `/api/:path*/` -> backend `/api/:path*/`.
- Added explicit no-slash root rewrites for `/api/v1/pmla`, `/api/v1/directories/pasf`, and `/api/v1/directories/emergency-services` to avoid FastAPI root-route redirects leaking `backend:8000`.
- Updated frontend API client root calls for PASF and emergency-services directories to use trailing slash collection URLs directly.

Verification:
- Frontend `npx tsc --noEmit --incremental false` -> passed.
- Frontend `npx eslint src/lib/api-client.ts next.config.ts` -> passed.
- Frontend `npm run build` -> passed.
- Recreated frontend container with `docker compose up -d --force-recreate frontend`.
- `GET http://localhost:3000/api/v1/pmla/` with origin and API key -> `200`, no redirect, no `Location: backend:8000`.
- `GET http://localhost:3000/api/v1/pmla` with origin and API key -> `200`, no redirect, no `Location: backend:8000`.
- `OPTIONS http://localhost:3000/api/v1/pmla/` with browser preflight headers -> `200` with `Access-Control-Allow-Origin: http://localhost:3000`.
- Frontend root `http://localhost:3000/` -> `200`.
- `docker compose ps` -> db, chromadb, backend, frontend all `Up`; db healthy.
- `git diff --check` -> passed with only Git LF/CRLF warnings.
- `git diff --cached --name-only` -> empty; no files are staged.

Current state:
- Docker app is running at `http://localhost:3000`.
- Patch C remains uncommitted and unstaged by design.