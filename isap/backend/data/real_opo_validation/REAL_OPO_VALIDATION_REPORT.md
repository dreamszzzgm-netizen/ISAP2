# PMLA Real OPO Validation #1 — Content Review

## Source
- **Facility:** Сеть газопотребления ул. Красная
- **Organization:** ИП Иванов Иван Иванович
- **Hazard class:** III
- **Equipment:** ШРП-МС-10 (РДГК-10М), газопровод ВД Ø108мм L=176м
- **Substance:** Природный газ (CAS 74-82-8)
- **Generated file:** `backend/data/real_opo_validation/real_opo_v2.docx`
- **Generation date:** 2026-07-10
- **Document ID:** c64c0939-40a7-47c1-862a-ae4116aa5df8

## Summary
- **Status:** Warning (score 12/100)
- **Main result:** DOCX successfully generated with real OPO data. Most sections are functional. Two critical content defects found: mojibake in custom scenario #6 and LLM hallucinated Chinese characters.

## What works

1. **Title page** — organization, facility, hazard class rendered correctly
2. **Approval sheet** — roles (разработал/проверил/утвердил) present
3. **Correction journal** — empty table with correct headers
4. **Abbreviations & terms** — standard PMLA content
5. **Introduction** — LLM-generated, references real facility data
6. **Section 1 (Characteristics)** — equipment table with ШРП-МС-10 specs
7. **Section 2 (Scenarios)** — 5 detailed scenarios with ПАЗ, technical means, action sequences
8. **Section 3 (Accident history)** — correctly states no incidents
9. **Section 4 (Forces)** — emergency services table structure
10. **Section 5 (Interaction)** — organization structure described
11. **Section 6 (Composition)** — personnel roles defined
12. **Section 7 (Readiness)** — readiness procedures
13. **Section 8 (Management)** — notification scheme table
14. **Section 9 (Information exchange)** — communication procedures
15. **Section 10 (Initial actions)** — step-by-step response procedures
16. **Section 11 (Personnel actions)** — role-based action descriptions
17. **Section 12 (Population safety)** — evacuation, medical, notification
18. **Section 13 (Material support)** — financial framework (generic)
19. **Special section (Operational)** — 6 scenarios with detailed technical content
20. **Appendices 1-5** — all generated with content
21. **Bibliography** — 22 regulatory documents
22. **Familiarization sheet** — table with correct person names
23. **Appendices manifest** — table with "сформировано" status
24. **Validation results** — 3 warnings shown

## Critical issues

### C1. Mojibake in custom scenario #6
**Location:** Special section, scenario 6
**Symptom:** `РѕР±СЂР°Р·РѕРІР°РЅРёРµ РІР·СЂС‹РІРѕРѕРїР°СЃРЅРѕР№ РіР°Р·РѕРІРѕР·РґСѓС€РЅРѕР№ СЃРјРµСЃРё`
**Expected:** "образование взрывоопасной газовоздушной смеси"
**Root cause:** The custom scenario description in the questionnaire context contains mojibake. This is the SAME encoding issue as the responsible persons — the SQL INSERT via PowerShell corrupted the UTF-8 data. The `custom_scenarios` field in `pmla_questionnaires.data` JSONB was inserted with corrupted text.
**Fix required:** Re-insert the questionnaire data with correct encoding via Python (same approach as responsible persons fix).

### C2. LLM hallucinated Chinese characters
**Location:** Section 2 (Scenarios), scenario 2 "Струйное горение газа", technical means
**Symptom:** `Огнетушители, водяное орошение, средства связи,熱画像 камера, защитные каски`
**Expected:** "тепловизор" or "тепловизионная камера"
**Root cause:** LLM generated a Japanese/Chinese term "熱画像" (thermal image) instead of Russian "тепловизор". This is a known LLM hallucination pattern for technical terms.
**Fix required:** Add post-processing filter for non-Cyrillic characters in LLM output, or use a fallback term.

## Important issues

### I1. Section 6 has no real emergency services data
**Location:** Section 6 (Состав и дислокация сил)
**Symptom:** Generic emergency services table with no real data
**Root cause:** `emergency_services` was empty in the questionnaire context
**Fix required:** User must fill emergency services data in the questionnaire. This is a data gap, not a code defect.

### I2. Notification scheme is empty
**Location:** Section 8 (Организация управления, связи и оповещения)
**Symptom:** Generic notification scheme with no real contacts
**Root cause:** `notification_scheme` was empty in the questionnaire context
**Fix required:** User must fill notification scheme. Data gap.

### I3. Financial reserve and insurance are absent
**Location:** Section 13 (Материально-техническое обеспечение)
**Symptom:** "Сведения о создании финансового резерва отсутствуют", "Сведения о договоре страхования отсутствуют"
**Root cause:** `financial_reserve` and `insurance` were empty in the questionnaire
**Fix required:** User must fill these fields. Data gap.

### I4. Appendix responsible persons show "— — —"
**Location:** Appendix 1, section 3 "Ответственные лица"
**Symptom:** `- Индивидуальный предприниматель: — — —`
**Root cause:** The template doesn't have access to responsible persons' contact details (phone, email) in the appendix context
**Fix required:** Template should render responsible persons with available data (name, position)

### I5. Bibliography contains foreign-language entries
**Location:** Bibliography, items 17 and 20
**Symptom:**
- Item 17: Contains Chinese characters `生产`
- Item 20: Contains English word `equipment`
**Root cause:** LLM generated bilingual text in bibliography entries
**Fix required:** Filter or post-process bibliography to ensure consistent Russian language

### I6. Familiarization sheet missing date and reg number
**Location:** Familiarization sheet
**Symptom:** `Регистрационный номер: —`, `Дата составления: —`
**Root cause:** `reg_number` is empty in the facility data, `document_date` not passed to template
**Fix required:** Pass `document_date` to context; use generation date as fallback

## Minor issues

### M1. Phone numbers still show bare "tel." in section 11
**Location:** Section 11, paragraph 357-358
**Symptom:** `- Иванов Иван Иванович — Индивидуальный предприниматель, тел. `
**Note:** The fix in `rules_engine.py` should have removed the "тел." part, but it still appears. This means the text comes from a different code path (possibly the Jinja2 template for section 11, not the rules engine).
**Fix required:** Check section 11 template rendering path

### M2. Validation results appended as plain text
**Location:** End of document
**Symptom:** `- [warning] Контакты: У Иванов Иван Иванович не указан телефон` appears as raw text
**Root cause:** Validation results are rendered as plain paragraphs, not in a table
**Fix required:** Format validation results in a proper table or omit from client-facing document

### M3. "Сведения об ОПО" form not integrated
**Location:** Throughout document
**Symptom:** No OPO details form data (OKTMO, registration number, etc.) appears in the document
**Root cause:** `opo_details` table exists but its data is not pulled into the generation context
**Fix required:** Add `opo_details.form_data` to the generation context

### M4. Some sections use generic fallback text
**Location:** Various sections
**Symptom:** Generic regulatory text instead of facility-specific content
**Root cause:** Missing questionnaire data triggers template fallbacks
**Fix required:** Data gap — not a code defect

## Manual engineer edits required

1. **Fill emergency services** — add real fire, medical, police, gas service data
2. **Fill notification scheme** — add real contact persons and phone numbers
3. **Fill financial reserve** — add order number, amount, date
4. **Fill insurance** — add company, contract number, validity
5. **Fill attachments checklist** — mark which appendices are actually available
6. **Add registration number** — if available from Rosreestr
7. **Add real document date** — set actual preparation date
8. **Review LLM-generated scenarios** — verify technical accuracy of 5 scenarios
9. **Review special section** — verify operational procedures match actual site layout
10. **Add real PASF data** — if a PASF is contracted for this facility

## Proposed fixes

### Fix 1: Custom scenario mojibake (CRITICAL)
Re-insert questionnaire data with correct encoding via Python inside Docker container.

### Fix 2: LLM Chinese character filter (CRITICAL)
Add post-processing in ScenarioEngine or NarrativeEngine to strip non-Cyrillic/non-standard characters from generated text.

### Fix 3: Appendix responsible persons (IMPORTANT)
Update `30_appendix_1.j2` template to render responsible persons with available data.

### Fix 4: Bibliography language filter (IMPORTANT)
Add post-processing to filter non-Russian text from bibliography entries.

### Fix 5: Document date fallback (IMPORTANT)
Pass `document_date` (generation date) to template context as fallback for missing date.

## Not in scope

- PDF merge
- RAG integration
- Geocoding
- Route calculation
- Electronic signatures (ЭЦП)
- Frontend redesign
- Major template restructuring
- Production deployment
