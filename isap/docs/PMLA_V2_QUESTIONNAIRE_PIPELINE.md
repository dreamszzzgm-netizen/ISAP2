# PMLA v2 Questionnaire Pipeline

**Date:** 2026-07-12
**Status:** V2 QUESTIONNAIRE PIPELINE READY
**Commit:** (not committed — awaiting E2E)

## Completed

1. **API** — `GenerateFromQuestionnaireRequest.template_version` (`"v1" | "v2"`) + `@field_validator`
2. **Service** — `PmlaGenerationFromQuestionnaireService.generate()` ветвит v1/v2
   - v1: без изменений → `EnhancedDocumentGenerator`
   - v2: `map_to_v2_context()` → `validate_v2_context()` → `PmlaTemplateRenderer` → DOCX → PDF
3. **Frontend API** — `api-client.ts`: `PmlaTemplateVersion` тип, `template_version` в payload
4. **Frontend UI** — две кнопки: «Сформировать ПМЛА v1» / «Сформировать PMLA v2 — пилот»
5. **Provenance** — `generation_meta` сохраняет `template_version`, `generation_pipeline`, `template_file`
6. **Mojibake check** — встроен в `_generate_v2()`
7. **Validation errors** — возвращаются как 400 с перечнем незаполненных полей

## Changed files (13 files, +724/-138)

| File | Changes |
|------|---------|
| `backend/src/api/routers/pmla_questionnaires.py` | +template_version field, 400/404 split |
| `backend/src/application/services/pmla_generation_from_questionnaire_service.py` | +_generate_v2() full pipeline |
| `backend/src/application/services/pmla_v2_context_mapper.py` | enhanced validation, container fallback |
| `frontend/src/lib/api-client.ts` | PmlaTemplateVersion type |
| `frontend/src/components/dashboard/pmla-questionnaire-page.tsx` | v1/v2 buttons |
| `frontend/src/components/dashboard/facility-detail-page.tsx` | v2 button |
| `docker-compose.yml` | +./files:/files volume mount |

## Known issues

- v2 generation fails validation if questionnaire data is incomplete (expected behaviour)
- Empty OGRN/INN in DB blocks v2 — fill organization data first
- mojibake check is best-effort (string-level, not XML-level)

## How to test

1. Fill all questionnaire blocks (organization, ОПО, equipment, substances, persons, PASF, emergency services)
2. Press «Сформировать PMLA v2 — пилот»
3. Check Network payload: `template_version: "v2"`
4. Check backend log: `requested_template_version=v2`, `selected_pipeline=pmla_template_renderer`
5. Result: DOCX ~6-12 MB based on pmla_v2_template.docx
