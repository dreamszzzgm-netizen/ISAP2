# Audit: material_reserve vs financial_reserve Conflict

## 1. Executive Summary

Two semantically different entities are conflated under the name `material_reserve`:

| Entity | Semantic meaning | Actual structure | Used by |
|--------|-----------------|-----------------|---------|
| **material_reserve** (schema) | LIST of physical items (СИЗ, инструмент, оборудование) for Table 13 | `[{name, quantity, location, is_group_header, group_name}]` | pmla_v2.schema.json §required_tables.material_reserve |
| **material_reserve** (runtime) | DICT with financial reserve + insurance data | `{fin_reserve_order, fin_reserve_amount, insurance_company, insurance_contract, ...}` | DataEngine._render_section_13, DocumentContext, pmla.py:81 |

Meanwhile, a third entity `financial_reserve` exists as a clean DICT `{created, order_number, order_date, amount}` in the questionnaire layer but is **never carried into DocumentContext** — it gets folded into `material_reserve` during adaptation.

## 2. Data Flow Trace

### 2.1 Questionnaire origin (clean)

`pmla_questionnaire_service.py:59-64` defines:
```python
"financial_reserve": {
    "created": None,
    "order_number": "",
    "order_date": "",
    "amount": "",
}
```

`pmla_quality_review_service.py:430-462` reads this correctly:
```python
financial = questionnaire.get("financial_reserve") or {}
created = financial.get("created")
order_number = financial.get("order_number")
amount = financial.get("amount")
```

### 2.2 Adaptation layer (the merge point)

`pmla_generation_from_questionnaire_service.py:211-245`:
```python
financial = questionnaire.get("financial_reserve") or {}
insurance = questionnaire.get("insurance") or {}
ctx["material_reserve"] = {
    "fin_reserve_order": self._join_order(financial),   # ← financial data
    "fin_reserve_amount": financial.get("amount"),
    "insurance_company": insurance.get("company"),       # ← insurance data
    "insurance_contract": insurance.get("contract_number"),
    "insurance_valid_until": insurance.get("valid_until"),
    "insurance_amount": insurance_amount,
}
```

The comment on line 211-212 explains the intent:
> Financial reserve and insurance are rendered by several engines under
> material_reserve/context_params names.

### 2.3 DocumentContext (type mismatch)

`base.py:93`:
```python
material_reserve: dict[str, Any] = field(default_factory=dict)
```

Type annotation says `dict`, but the schema says this should be a `list`. The actual runtime usage is a dict containing financial+insurance data — not the physical items list from the schema.

### 2.4 DataEngine renderer (consumes the merged dict)

`data_engine.py:567-643` (`_render_section_13`):
```python
reserve = ctx.material_reserve or {}
order = reserve.get("fin_reserve_order", "")
amount = reserve.get("fin_reserve_amount", "")
# ... renders financial reserve paragraph
# ... renders insurance paragraph from same reserve dict
```

This renderer produces "Материально-техническое обеспечение" section — which is about **financial** reserve and insurance, NOT physical items.

### 2.5 pmla.py debug endpoint (the conflict site)

`pmla.py:81-87`:
```python
reserve = context.get("financial_reserve", context.get("material_reserve"))
checks["financial_reserve"] = {
    "present": "financial_reserve" in context or "material_reserve" in context,
    "non_empty": bool(reserve),
    "type": type(reserve).__name__ if reserve is not None else None,
    "source_key": "financial_reserve" if "financial_reserve" in context else "material_reserve",
}
```

This code:
1. Tries `context.get("financial_reserve")` — this key **never exists** in the adapted context
2. Falls back to `context.get("material_reserve")` — which is the financial+insurance dict
3. Labels it `checks["financial_reserve"]` — creating a false impression that `financial_reserve` was found

### 2.6 Enhanced generator (another merge point)

`enhanced_generator.py:241-253`:
```python
"material_reserve": {
    "sip_amount": "—",
    "sip_source": "—",
    "fire_amount": "—",
    # ... more financial-looking defaults
},
enriched["material_reserve"].update(context.get("material_reserve") or {})
```

Same pattern: `material_reserve` is a dict with financial amounts, not physical items.

### 2.7 Debug sample (confirms the pattern)

`pmla_debug_sample.py:158-162`:
```python
"material_reserve": {
    "fin_reserve_order": "№80-П от 19.02.2026",
    "fin_reserve_amount": "250 000 (двести пятьдесят тысяч) рублей",
    "insurance_company": "АО «СОГАЗ»",
},
```

## 3. Schema vs Runtime Comparison

### Schema definition (`pmla_v2.schema.json:138-152`)

```json
"material_reserve": {
    "description": "Таблица 13 — материально-техническое обеспечение",
    "item_fields": {
        "name": "Наименование",
        "quantity": "Количество",
        "location": "Место расположения",
        "is_group_header": "Булево",
        "group_name": "Название группы"
    },
    "source": "manual"
}
```

This is a **LIST of physical inventory items** for the物资保障 table.

### Runtime shape (what engines actually receive)

```python
{
    "fin_reserve_order": "12-ПБ от 2026-01-15",
    "fin_reserve_amount": "500000",
    "insurance_company": "АО Страховая компания",
    "insurance_contract": "ГО-123456",
    "insurance_valid_until": "2027-01-15",
    "insurance_amount": "10000000",
}
```

This is a **DICT of financial metadata** — completely different structure and semantics.

## 4. Three Distinct Entities

### Entity A: `financial_reserve` (questionnaire layer)
- **Structure**: `{created: bool, order_number: str, order_date: str, amount: str, responsible: str}`
- **Purpose**: Tracks whether a financial reserve was created, via what order, and how much
- **Read by**: `PmlaQualityReviewService._check_financial_reserve()` (quality review)
- **Problem**: Never flows into `DocumentContext` as its own field; gets folded into `material_reserve`

### Entity B: `material_reserve` (adapted/runtime layer)
- **Structure**: `{fin_reserve_order, fin_reserve_amount, insurance_company, insurance_contract, ...}`
- **Purpose**: Holds financial+insurance data merged together for section 13 rendering
- **Read by**: `DataEngine._render_section_13()`, `pmla.py` debug endpoint
- **Problem**: Misnamed — contains zero physical items; it's a financial+insurance bundle

### Entity C: `material_reserve` (schema/-template layer)
- **Structure**: `[{name, quantity, location, is_group_header, group_name}]`
- **Purpose**: Physical inventory items (СИЗ, инструмент, оборудование) for Table 13
- **Read by**: Template rendering (docxtpl via `material_reserve` jinja tag)
- **Problem**: Schema defines this but nothing in the engine pipeline populates it as a list

## 5. Impact Analysis

### 5.1 DataEngine._render_section_13 (data_engine.py:567-643)
- Reads `ctx.material_reserve` expecting financial data dict
- Renders "Финансовый резерв" paragraph from `fin_reserve_order` and `fin_reserve_amount`
- Renders insurance from the same dict's `insurance_company`, `insurance_contract` keys
- **Impact**: Works correctly at runtime because the adapted context provides the right shape

### 5.2 pmla.py debug endpoint (pmla.py:81)
- Tries `context.get("financial_reserve")` — always `None`/missing in adapted context
- Falls back to `context.get("material_reserve")` — gets the financial dict
- Reports it under `checks["financial_reserve"]` with `source_key: "material_reserve"`
- **Impact**: Misleading debug output; suggests `financial_reserve` exists when it doesn't

### 5.3 Schema mismatch
- Schema says `material_reserve` is a list of physical items
- Runtime delivers a dict of financial data
- If template rendering ever uses the schema shape, it will break
- **Impact**: Silent data loss for physical inventory if Table 13 needs actual items

### 5.4 Quality review separation
- `PmlaQualityReviewService._check_financial_reserve()` reads `questionnaire.financial_reserve` directly
- This is the original clean data — no conflict here
- But `pmla.py:81` conflates the two, creating confusion in debug output
- **Impact**: Debug endpoint and quality review disagree on what "financial_reserve" means

### 5.5 Insurance data duplication
- Insurance appears in THREE places: `ctx["material_reserve"]`, `ctx["insurance"]`, and `ctx["context_params"]`
- `DataEngine._render_section_13` reads from `ctx.material_reserve` first, falls back to `ctx.insurance`
- **Impact**: Fragile fallback chain; if one is missing/wrong, the other may have stale data

## 6. Recommended Changes

### 6.1 Rename runtime `material_reserve` → `financial_provision`

**Files to change**:
- `base.py:93` — rename field `material_reserve` → `financial_provision`
- `base.py:123,152` — update `from_dict`/`to_dict` mappings
- `engine_integration.py:106` — update key name
- `data_engine.py:583` — update `ctx.material_reserve` → `ctx.financial_provision`
- `pmla_generation_from_questionnaire_service.py:223,242-244` — update dict key
- `enhanced_generator.py:241,253` — update dict key
- `pmla_debug_sample.py:158` — update sample data
- `pmla.py:81-87` — update debug checks

### 6.2 Restore schema `material_reserve` as physical items list

**Files to change**:
- `pmla_v2.schema.json` — keep `material_reserve` as the LIST definition (already correct)
- `base.py` — add `material_reserve_items: list[dict] = field(default_factory=list)` for physical items
- `engine_integration.py` — populate `material_reserve_items` from questionnaire `organization_resources.actual_items`

### 6.3 Fix pmla.py debug endpoint

**Current** (line 81):
```python
reserve = context.get("financial_reserve", context.get("material_reserve"))
```

**Fixed**:
```python
financial_reserve = context.get("financial_reserve")
financial_provision = context.get("financial_provision")
checks["financial_reserve"] = {
    "present": bool(financial_reserve),
    "non_empty": bool(financial_reserve),
    "type": type(financial_reserve).__name__,
}
checks["financial_provision"] = {
    "present": bool(financial_provision),
    "non_empty": bool(financial_provision),
    "type": type(financial_provision).__name__,
}
```

### 6.4 Consolidate insurance data

**Current**: Insurance in `material_reserve`, `insurance`, and `context_params`

**Recommended**: Keep insurance only in `ctx["insurance"]` (already exists). Remove insurance keys from `financial_provision`. Update `DataEngine._render_section_13` to read from `ctx.insurance` directly.

### 6.5 Minimum viable fix (if full rename is too risky)

If renaming `material_reserve` → `financial_provision` across the codebase is too large:

1. **pmla.py:81** — change to read from the correct key:
   ```python
   reserve = context.get("financial_provision") or context.get("material_reserve")
   ```
2. **base.py:93** — add comment clarifying the misnomer:
   ```python
   material_reserve: dict[str, Any] = field(default_factory=dict)  # NOTE: despite the name, this holds financial+insurance data, NOT physical items
   ```
3. **Schema** — keep `material_reserve` as-is for template rendering of physical items; it's a separate concern

## 7. Test Coverage Gaps

- `test_pmla_questionnaire_docx_output.py:142-147` — test data uses `material_reserve` with `fin_reserve_order` keys, confirming the runtime shape but not testing the schema's list shape
- `test_pmla_questionnaire_docx_output.py:196-205` — `test_material_reserve_financial` validates the merged dict, not the schema shape
- No test verifies that `material_reserve` as a list of physical items renders correctly in a template
- No test verifies the `pmla.py` debug endpoint output is semantically correct

## 8. Risk Assessment

| Risk | Severity | Likelihood |
|------|----------|------------|
| Debug endpoint misreports financial_reserve presence | Low | High (always triggers fallback) |
| Schema/shape mismatch causes template rendering failure | Medium | Low (template not yet wired) |
| Insurance data inconsistency across 3 copies | Medium | Medium (fallback chain) |
| Physical items (СИЗ/инструмент) never reach Table 13 | Medium | High (no code populates list) |
| Renaming breaks downstream consumers | High | Medium (if done carelessly) |

## 9. Conclusion

The conflict is real but currently **non-blocking** because:
1. The questionnaire adaptation layer transforms `financial_reserve` → `material_reserve` dict at runtime
2. DataEngine reads the dict correctly for section 13 rendering
3. Quality review reads the original questionnaire data directly

The main risks are:
- **Semantic confusion**: anyone reading the code thinks `material_reserve` = physical items, but it's financial data
- **Schema divergence**: the schema definition will never match the runtime shape without explicit bridging
- **Future breakage**: if template rendering or a new consumer expects the schema shape, it will silently get an empty dict
