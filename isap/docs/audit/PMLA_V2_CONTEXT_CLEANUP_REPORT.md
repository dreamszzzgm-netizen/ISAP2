# PMLA v2 Empty Render — Test Data Source Audit

**Date:** 2026-07-11
**Status:** READ-ONLY ANALYSIS

---

## Summary

The test data found in the "empty" render (`ООО ТестПром` 65x, `ООО Спас` 24x, `Иванов И.И.` 4x) originates from the **test scripts' scalar context values**, NOT from the template headers or renderer defaults. The empty render is only "empty" for **list fields** — all scalar/string values are preserved from the full context.

---

## Finding 1: Template Headers — CLEAN

**`files/pmla_v2_template.docx` → `word/header1.xml`**

The template header contains only Jinja2 placeholders, no hardcoded test data:

```
План мероприятий по локализации и ликвидации последствий аварий на ОПО
«Сеть газопотребления {{ organization_short_name }}  рег. № {{ facility_reg_number }}
```

**Verdict:** Template headers are NOT the source. They use `{{ organization_short_name }}` and `{{ facility_reg_number }}` — values are injected at render time.

---

## Finding 2: Renderer — CLEAN

**`backend/src/infrastructure/export/pmla_template_renderer.py`**

The renderer has no default values, no fallbacks, and no hardcoded test data. It passes the context dict directly to `docxtpl`:

- Line 55: `doc = DocxTemplate(str(self.template_path))`
- Line 56: `doc.render(context)`

**Verdict:** The renderer is NOT the source. It renders whatever context is provided.

---

## Finding 3: Root Cause — Empty Context Construction in Scripts

All three render scripts create "empty" contexts by clearing **only list fields**, while preserving all scalar fields with hardcoded test values.

### 3a. `verify_final_render.py` (line 8, 68)

```python
# Lines 7-50: Full context with hardcoded test data
ctx = {
    'organization_full_name': 'ООО ТестПром',          # line 8
    'organization_short_name': 'ООО ТестПром',          # line 8
    'director_position_fullname': 'Генеральный директор Иванов И.И.',  # line 11
    'contractor_organization_name': 'ООО Спас',         # line 17
    ...
}

# Line 68: Empty = only lists cleared, scalars kept
empty_ctx = {k: ([] if isinstance(v, list) else v) for k, v in ctx.items()}
```

### 3b. `full_render_and_pdf.py` (lines 10-207, 210)

```python
# Lines 10-207: Full context with hardcoded test data
FULL_CTX = {
    'organization_full_name': 'Общество с ограниченной ответственностью «КавказГазСервис»',
    'contractor_organization_name': 'ООО «Региональное объединение спасателей «Спас»',
    ...
}

# Line 210: Empty = only lists cleared, scalars kept
EMPTY_CTX = {k: ([] if isinstance(v, list) else v) for k, v in FULL_CTX.items()}
```

### 3c. `test_pmla_v2_render.py` (lines 20-228)

```python
# Lines 20-216: FULL_CONTEXT with hardcoded test data
FULL_CONTEXT = {
    "organization_full_name": "Общество с ограниченной ответственностью «ТестПром»",
    "contractor_organization_name": "ООО «Спасатель»",
    ...
}

# Lines 219-228: Empty = only specific list fields cleared
EMPTY_CONTEXT = {**FULL_CONTEXT}
EMPTY_CONTEXT["equipment_list"] = []
EMPTY_CONTEXT["substance_params"] = []
# ... (9 list fields cleared, all scalars kept)
```

---

## Finding 4: Schema Alignment Test — Same Pattern

**`backend/tests/infrastructure/export/test_pmla_v2_schema_alignment.py`** (lines 434-545)

```python
def _build_full_context() -> dict:       # line 434
    return {
        "organization_full_name": "ООО «ТестПром»",    # line 437
        "director_position_fullname": "Генеральный директор Иванов И.И.",  # line 444
        "contractor_organization_name": "ООО «Спасатель»",  # line 455
        ...
    }

def _build_empty_context() -> dict:      # line 536
    """All list fields empty, scalars kept."""  # <-- by design
    ctx = _build_full_context()
    for key in ["equipment_list", "substance_params", ...]:
        ctx[key] = []
    return ctx
```

The docstring on line 537 explicitly states: **"All list fields empty, scalars kept."** This is by design — the test validates that the template handles empty lists without crashing, not that all values are blank.

---

## Complete Test Data Inventory

| String | Occurrences in EMPTY render | Source files with hardcoded values |
|--------|---------------------------|-----------------------------------|
| `ООО ТестПром` | 65x | `verify_final_render.py:8`, `test_pmla_v2_render.py:22-23`, `test_pmla_v2_schema_alignment.py:437-438` |
| `ООО Спас` / `«Спас»` / `«Спасатель»` | 24x | `verify_final_render.py:17`, `full_render_and_pdf.py:36-37`, `test_pmla_v2_render.py:44-45`, `test_pmla_v2_schema_alignment.py:455-456` |
| `Иванов И.И.` / `Иванов Иван Иванович` | 4x | `verify_final_render.py:11-12`, `full_render_and_pdf.py:19-21`, `test_pmla_v2_render.py:29-31`, `test_pmla_v2_schema_alignment.py:444-446` |

---

## Why This Happens

The PMLA template uses Jinja2 `{% for %}` loops for list tables (equipment, scenarios, countermeasures, etc.) and simple `{{ variable }}` substitution for scalars (org name, director, etc.).

When the "empty" context clears only lists:
- **Tables 5-13** (list-based): Empty rows or hidden — correct behavior
- **Scalars** (org name, director, phones): Rendered with hardcoded test values — appears as "test data in empty render"

The empty render was designed to test **list-empty handling**, not a fully blank document.

---

## Recommendation (DO NOT EDIT — analysis only)

To produce a truly empty render for validation, the empty context should use blank strings for all scalar fields:

```python
truly_empty_ctx = {k: "" if isinstance(v, str) else ([] if isinstance(v, list) else v) for k, v in FULL_CONTEXT.items()}
```

Or create a separate `EMPTY_CONTEXT` with explicitly blanked scalars rather than inheriting from `FULL_CONTEXT`.

**Files that would need changes (if fixes were approved):**
1. `backend/scripts/verify_final_render.py` — line 68
2. `backend/scripts/full_render_and_pdf.py` — line 210
3. `backend/scripts/test_pmla_v2_render.py` — lines 219-228
4. `backend/tests/infrastructure/export/test_pmla_v2_schema_alignment.py` — lines 536-545

---

## Files Analyzed

| File | Contains test data? | Role |
|------|-------------------|------|
| `files/pmla_v2_template.docx` (header1.xml) | **No** — uses `{{ placeholders }}` | Template source |
| `backend/src/infrastructure/export/pmla_template_renderer.py` | **No** — no defaults | Renderer engine |
| `backend/scripts/verify_final_render.py` | **Yes** — lines 8, 11, 17 | Test script with hardcoded ctx |
| `backend/scripts/full_render_and_pdf.py` | **Yes** — lines 12-13, 19, 36 | Test script with hardcoded ctx |
| `backend/scripts/test_pmla_v2_render.py` | **Yes** — lines 22-23, 29, 44 | Test script with hardcoded ctx |
| `backend/tests/infrastructure/export/test_pmla_v2_schema_alignment.py` | **Yes** — lines 437, 444, 455 | Test builder with hardcoded ctx |
