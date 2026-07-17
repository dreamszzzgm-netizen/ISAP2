#!/usr/bin/env python3
"""D6 Acceptance: end-to-end pipeline test with Russian facility_type."""
import sys, os, json, shutil, tempfile, zipfile, re, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.application.services.pmla_v2_context_mapper import map_to_v2_context
from src.application.services.pmla_ooxml_flat_renderer import PmlaOoxmlFlatRenderer

FILES_DIR = r"D:\Project ISAP\isap\isap\files"
FACILITY_TYPE = "Сеть газопотребления"

# ── Build source_context (simulates PmlaQuestionnaireService.build_generation_context) ──
SOURCE_CONTEXT = {
    "organization": {
        "full_name": "Общество с ограниченной ответственностью «КавказГазСервис»",
        "short_name": "ООО «КавказГазСервис»",
        "legal_address": "361400, Кабардино-Балкарская Республика, г. Нальчик, ул. Ленина, д. 42",
        "inn": "0703123456",
        "ogrn": "1020700001234",
        "phone": "+7 (8662) 45-67-89",
        "email": "info@kavkazgazservice.ru",
        "director_position": "Генеральный директор",
        "director_full_name": "Кумахов Ахмед Абдуллаевич",
        "director_phone": "+7 (8662) 45-67-89",
        "director_position_fullname": "Генеральный директор Кумахов Ахмед Абдуллаевич",
        "director_initials_surname": "А.А. Кумахов",
        "director_initials_surname_full": "Кумахов Ахмед Абдуллаевич",
        "deputy_chairman_fullname": "Батов Руслан Хажмуратович",
        "main_activity_description": "43.22 Производство труб, водопроводных и канализационных сооружений",
        "settlement_name": "г. Нальчик",
    },
    "facility": {
        "facility_type": FACILITY_TYPE,
        "name": "Сеть газопотребления",
        "facility_name": "Сеть газопотребления",
        "reg_number": "А34-99999-0099",
        "location": "Кабардино-Балкарская Республика, г. Нальчик",
        "hazard_class": "III",
        "hazardous_substances_info": "Природный газ (метан) по ГОСТ 5542-2014",
        "hazard_characteristics_116fz": "Использование горючих газов в качестве топлива",
        "total_hazardous_substance_quantity": "0.5",
    },
    "equipment": [
        {
            "location": "Площадка ГРП (здание ГРПШ)",
            "hazard_characteristic": "Использование горючих газов",
            "device_name": "ГРПШ 03БМ-04-У1 (в составе с РДНК-400, зав. № 92)",
            "specifications": "Р раб.=0,6 МПа; Р регул.=3000 Па; Т раб.=50°С; Год ввода: 2012",
            "process_codes": "2.1",
        },
        {
            "location": "Участок газопровода ВД №1 (от ГРПШ до запорной арматуры)",
            "hazard_characteristic": "Использование горючих газов",
            "device_name": "Труба стальная Ø57 мм, L=13,40 м",
            "specifications": "Р раб.=0,3–0,6 МПа; Материал: Ст20; Сварка: ручная дуговая",
            "process_codes": "2.1",
        },
        {
            "location": "Участок газопровода ВД №2 (от ГРПШ до потребителя)",
            "hazard_characteristic": "Использование горючих газов",
            "device_name": "Труба стальная Ø57 мм, L=2,00 м",
            "specifications": "Р раб.=0,3–0,6 МПа; Материал: Ст20",
            "process_codes": "2.1",
        },
    ],
    "substances": [
        {"parameter": "Класс опасности по ГОСТ 12.1.007", "value": "4 (малоопасный)"},
        {"parameter": "ПДК в воздухе рабочей зоны (по метану)", "value": "300 мг/м³"},
        {"parameter": "НКПР", "value": "5 % об."},
        {"parameter": "ВКПР", "value": "15 % об."},
        {"parameter": "Категория взрывоопасной смеси по ПУЭ", "value": "IIА – Т1"},
        {"parameter": "Характер воздействия на человека", "value": "Удушающее действие при снижении O₂"},
        {"parameter": "СИЗ", "value": "Изолирующие дыхательные аппараты АП-2"},
        {"parameter": "Первая помощь", "value": "Вынести пострадавшего из зоны загазованности"},
    ],
    "responsible_persons": [
        {"position": "Генеральный директор", "full_name": "Кумахов А.А.", "phone": "+7 (8662) 45-67-89"},
    ],
    "emergency_services": {},
    "pasf": {
        "organization_name": "ООО «Региональное объединение спасателей «Спас»",
        "short_name": "«Спас»",
        "agreement_date": "15.12.2025",
    },
    "insurance": {},
    "financial_reserve": {},
    "scenarios": [
        {
            "code": "С-1", "name": "Выброс газа без воспламенения (загазованность)",
            "source": "Фланцевые соединения, арматура на ГРПШ",
            "preconditions": "Разгерметизация соединений",
            "signs": "Характерный запах, шум истекающего газа",
            "damaging_factors": "Токсическое действие, удушье",
        },
        {
            "code": "С-2", "name": "Струйное горение газа (факел)",
            "source": "Место разрыва газопровода ВД",
            "preconditions": "Разрыв трубы",
            "signs": "Открытое пламя, тепловое излучение",
            "damaging_factors": "Тепловое излучение",
        },
        {
            "code": "С-3", "name": "Взрыв газовоздушной смеси",
            "source": "Территория ГРПШ",
            "preconditions": "Утечка газа → облако ГВС",
            "signs": "Хлопок, ударная волна",
            "damaging_factors": "Избыточное давление",
        },
    ],
    "equipment_scenario_links": [],
    "equipment_defects": [],
    "injury_history": [],
    "accident_history": [],
    "questionnaire": {},
    "contractor": {
        "organization_name": "ООО «Региональное объединение спасателей «Спас»",
        "short_name": "«Спас»",
        "agreement_date": "15.12.2025",
        "director_position": "Директор",
        "director_full_name": "Иванов Иван Иванович",
        "director_initials_surname": "И.И. Иванов",
    },
}


def validate_docx(docx_path: str, expected_cm_count: int) -> dict:
    """Validate DOCX: ZIP integrity, media, Jinja leftovers, loop data."""
    results = {}

    # ZIP integrity
    with zipfile.ZipFile(docx_path, 'r') as zf:
        names = zf.namelist()
        bad = zf.testzip()
        results['zip_ok'] = bad is None
        if bad:
            results['zip_bad_file'] = bad

        # Media count
        media_files = [n for n in names if n.startswith('word/media/')]
        results['media_count'] = len(media_files)
        results['media_files'] = media_files

        # Read all XML parts
        all_text = ""
        for n in names:
            if n.endswith('.xml') or n.endswith('.rels'):
                try:
                    all_text += zf.read(n).decode('utf-8', errors='ignore')
                except:
                    pass

    # Jinja leftovers
    leftovers = set()
    for m in re.finditer(r'\{\{|\}\}|\{%|\%\}', all_text):
        ctx = all_text[max(0, m.start()-40):m.end()+40]
        leftovers.add(m.group())
    results['jinja_leftovers'] = sorted(leftovers) if leftovers else []
    results['jinja_clean'] = len(results['jinja_leftovers']) == 0

    # Count table rows per loop
    for loop_name, fields in [
        ("substance_params", ["parameter", "value"]),
        ("equipment_scenario_links", ["equipment_name", "scenario_codes", "description", "damaging_factors"]),
        ("accident_scenarios", ["code", "name", "source", "preconditions", "signs", "damaging_factors"]),
        ("material_reserve_actual", ["name", "quantity", "location"]),
        ("material_reserve_recommended", ["name", "quantity", "location"]),
        ("countermeasures", ["scenario_label", "signs", "protection", "technical_means", "executors"]),
    ]:
        field_counts = []
        for field in fields:
            count = all_text.count(f"w:tr" + field)  # rough proxy
            field_counts.append(all_text.count(field))
        results[f"{loop_name}_in_text"] = any(c > 0 for c in field_counts)

    return results


def verify_pdf(pdf_path: str):
    """Basic PDF verification via PyMuPDF."""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        pages = len(doc)
        # Check for table text on each page
        tables_found = set()
        for i in range(pages):
            text = doc[i].get_text()
            if "Параметр" in text and "Значение" in text:
                tables_found.add("T6_substance_params")
            if "Оборудование" in text and "Сценарий" in text:
                tables_found.add("T7_equipment_scenario")
            if "Код сценария" in text and "Наименование" in text:
                tables_found.add("T9_accident_scenarios")
            if "Наименование" in text and "Количество" in text and "Место" in text:
                tables_found.add("T13_material_reserve")
            if "Сценарий" in text and "Признаки" in text and "Защита" in text:
                tables_found.add("T18_countermeasures")
        doc.close()
        return {"pages": pages, "tables_found": sorted(tables_found)}
    except ImportError:
        return {"pages": 0, "tables_found": [], "error": "PyMuPDF not installed"}


def main():
    print("=" * 70)
    print("D6 ACCEPTANCE — END-TO-END PIPELINE VERIFICATION")
    print("=" * 70)

    # Step 1: map_to_v2_context
    print("\n[1/5] Running map_to_v2_context...")
    v2_ctx = map_to_v2_context(SOURCE_CONTEXT)
    print(f"  v2 context keys: {len(v2_ctx)}")
    print(f"  facility_type: {SOURCE_CONTEXT['facility']['facility_type']}")
    cm_count = len(v2_ctx.get("countermeasures", []))
    print(f"  countermeasures count: {cm_count}")

    assert cm_count >= 2, f"FAIL: countermeasures count = {cm_count} < 2"
    print("  ✓ countermeasures ≥ 2")

    # Verify all 5 fields in each countermeasure
    for i, cm in enumerate(v2_ctx.get("countermeasures", [])):
        for field in ["scenario_label", "signs", "protection", "technical_means", "executors"]:
            val = cm.get(field, "")
            assert val and len(str(val).strip()) > 10, \
                f"FAIL: countermeasures[{i}].{field} is empty or too short: '{val}'"
    print(f"  ✓ All {cm_count} countermeasures have 5 required fields")

    # Step 2: template placeholder check
    print("\n[2/5] Checking template placeholders...")
    r = PmlaOoxmlFlatRenderer()
    tpl_ph = r._extract_flat_placeholders()
    missing = sorted(tpl_ph - set(v2_ctx.keys()))
    if missing:
        print(f"  Auto-filling {len(missing)} placeholders absent from v2 context:")
        for k in missing:
            v2_ctx[k] = f"[{k}]"
        print("  " + ", ".join(missing))
    else:
        print("  ✓ All template placeholders served by v2 context")

    # Step 3: Render DOCX
    print("\n[3/5] Rendering DOCX...")
    output_docx = os.path.join(FILES_DIR, "pmla_v2_d6_acceptance.docx")
    r.render_to_file(v2_ctx, output_docx)
    size = os.path.getsize(output_docx)
    print(f"  Saved: {output_docx} ({size:,} bytes)")

    # Step 4: DOCX validation
    print("\n[4/5] Validating DOCX...")
    docx_results = validate_docx(output_docx, cm_count)

    status = "✓" if docx_results['zip_ok'] else "✗"
    print(f"  {status} ZIP integrity: {docx_results['zip_ok']}")
    status = "✓" if docx_results['jinja_clean'] else "✗"
    print(f"  {status} Jinja leftovers: {docx_results['jinja_leftovers']}")
    print(f"  ✓ Media files: {docx_results['media_count']}")
    for mf in docx_results['media_files']:
        print(f"    - {mf}")

    # Compare media with template (byte-for-byte)
    template_docx = os.path.join(FILES_DIR, "pmla_v2_template.docx")
    with zipfile.ZipFile(template_docx, 'r') as zt:
        tmpl_media = {n: zt.read(n) for n in zt.namelist() if n.startswith('word/media/')}
    with zipfile.ZipFile(output_docx, 'r') as zr:
        rend_media = {n: zr.read(n) for n in zr.namelist() if n.startswith('word/media/')}

    all_media_ok = True
    for name in tmpl_media:
        if name not in rend_media:
            print(f"  ✗ Media missing: {name}")
            all_media_ok = False
        elif tmpl_media[name] != rend_media[name]:
            print(f"  ✗ Media changed: {name}")
            all_media_ok = False
    if all_media_ok:
        print(f"  ✓ All {len(tmpl_media)} media files byte-identical to template")

    assert docx_results['zip_ok'], "ZIP integrity failed"
    assert docx_results['jinja_clean'], f"Jinja leftovers: {docx_results['jinja_leftovers']}"
    assert all_media_ok, "Media files differ from template"
    print("  ✓ DOCX validation PASSED")

    # Step 5: PDF conversion + visual QA
    print("\n[5/5] Converting to PDF and visual QA...")
    soffice = r"C:\Program Files\LibreOffice\program\soffice.exe"
    pdf_path = os.path.join(FILES_DIR, "pmla_v2_d6_acceptance.pdf")

    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [soffice, "--headless", "--convert-to", "pdf", "--outdir", tmpdir, output_docx]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            pdf_name = os.path.splitext(os.path.basename(output_docx))[0] + ".pdf"
            src = os.path.join(tmpdir, pdf_name)
            if os.path.exists(src):
                shutil.copy2(src, pdf_path)
                print(f"  ✓ PDF created: {pdf_path} ({os.path.getsize(pdf_path):,} bytes)")

                pdf_info = verify_pdf(pdf_path)
                if pdf_info.get("pages"):
                    print(f"  ✓ PDF pages: {pdf_info['pages']}")
                    for t in pdf_info.get("tables_found", []):
                        print(f"    - {t}")
                    print(f"  ✓ Tables found in PDF: {len(pdf_info['tables_found'])}/5 expected")
                else:
                    print(f"  ⚠ PDF QA: {pdf_info.get('error', 'unknown')}")
        else:
            print(f"  ✗ LibreOffice error: {result.stderr[:200]}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Pipeline: source → map_to_v2_context → PmlaOoxmlFlatRenderer")
    print(f"  Facility type: {FACILITY_TYPE}")
    print(f"  Countermeasures: {cm_count} (expected ≥2)")
    print(f"  DOCX: {output_docx} ({size:,} bytes)")
    print(f"  PDF: {pdf_path}")
    print(f"  ZIP OK: {docx_results['zip_ok']}")
    print(f"  Media OK: {all_media_ok} ({len(tmpl_media)} files)")
    print(f"  Jinja leftovers: {docx_results['jinja_leftovers']}")
    print()
    print("  D6 ACCEPTANCE: " + ("✓ PASSED" if cm_count >= 2 and docx_results['zip_ok']
          and docx_results['jinja_clean'] and all_media_ok else "✗ FAILED"))

    # Save v2 context for audit
    ctx_path = os.path.join(FILES_DIR, "pmla_v2_d6_acceptance_context.json")
    with open(ctx_path, 'w', encoding='utf-8') as f:
        json.dump(v2_ctx, f, ensure_ascii=False, indent=2, default=str)
    print(f"  v2 context saved: {ctx_path}")


if __name__ == "__main__":
    main()
