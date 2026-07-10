# Real OPO Validation #4 — Second Facility Type (Boiler)

## Facility
- **Type:** Котельная
- **Name:** Котельная производственной площадки
- **Organization:** ООО "ТеплоСервис"
- **Hazard class:** III
- **Equipment:** Котёл КВ-ГМ-0.7, Горелка ГМГ-100, Газопровод НД, Насос ЦН-32/50
- **Substance:** Природный газ (CAS 74-82-8)
- **Generated file:** `backend/data/real_opo_validation/real_opo_boiler.docx`

## KG Context
- **Facility type:** котельная
- **Equipment types:** котёл, горелка, трубопроводы, арматура, САБ
- **Hazards:** взрыв котла, пожар, отказ САБ, понижение уровня воды, повышение давления
- **Recommended scenarios:** 5 (отказ САБ, понижение уровня воды, взрыв, пожар, утечка газа)
- **Required services:** пожарная охрана, скорая медицинская помощь
- **Required appendices:** схема расположения, схема оповещения, перечень сил и средств
- **Applicable regulations:** ГОСТ Р 22.10.03-2020, Приказ №472, ФЗ-116

## RAG Context
- **RAG adapter:** active, in-memory fallback
- **RAG chunks consumed:** Yes (in section_2, section_10)
- **Gas network contamination:** FIXED (was present before fix)

## DOCX Result
- **Total paragraphs:** 448
- **Total words:** 2773
- **Mojibake:** 0
- **Chinese:** 0
- **Gas-network terms:** 0 (fixed)

## Quality Review
- **Status:** warning (data gaps, not code issues)
- **Critical:** 0
- **Warnings:** 3 (phones missing, GOST not in registry)

## Issues

### Critical (fixed)
| Issue | Fix |
|-------|-----|
| section_10 contained gas network scenarios (ГРПШ) for boiler | Removed gas network fallback in `_render_section_10` |

### Important
None found.

### Minor
- Warning: phones missing for responsible persons (data gap)
- Warning: GОСТ Р 22.10.03-2020 not in regulatory registry

### Later
- Add scenario_instructions for Котельная type
- Add more boiler-specific RAG content

## Decision
Boiler DOCX is valid. The critical gas-network contamination was fixed. No other critical issues found.
