"""Baseline PMLA generation check вЂ” Р·Р°РїСѓСЃС‚РёС‚СЊ Р”Рћ Рё РџРћРЎР›Р• РёР·РјРµРЅРµРЅРёР№ РѕСЂРіР°РЅРёР·Р°С†РёРё."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.application.services.pmla_v2_context_mapper import map_to_v2_context
from src.application.services.pmla_ooxml_flat_renderer import PmlaOoxmlFlatRenderer
from pathlib import Path

FILES_DIR = Path(__file__).resolve().parents[2] / "files"

# Minimal source context with current org fields
SOURCE_CTX = {
    "organization": {
        "id": "00000000-0000-0000-0000-000000000001",
        "name": "РћРћРћ В«РљР°РІРєР°Р·Р“Р°Р·РЎРµСЂРІРёСЃВ»",
        "full_name": "РћР±С‰РµСЃС‚РІРѕ СЃ РѕРіСЂР°РЅРёС‡РµРЅРЅРѕР№ РѕС‚РІРµС‚СЃС‚РІРµРЅРЅРѕСЃС‚СЊСЋ В«РљР°РІРєР°Р·Р“Р°Р·РЎРµСЂРІРёСЃВ»",
        "short_name": "РћРћРћ В«РљР°РІРєР°Р·Р“Р°Р·РЎРµСЂРІРёСЃВ»",
        "inn": "0703123456",
        "ogrn": "1020700001234",
        "address": "361400, РљР°Р±Р°СЂРґРёРЅРѕ-Р‘Р°Р»РєР°СЂСЃРєР°СЏ Р РµСЃРїСѓР±Р»РёРєР°, Рі. РќР°Р»СЊС‡РёРє, СѓР». Р›РµРЅРёРЅР°, Рґ. 42",
        "phone": "+7 (8662) 45-67-89",
        "email": "info@kavkazgazservice.ru",
    },
    "facility": {
        "id": "00000000-0000-0000-0000-000000000002",
        "facility_type": "РЎРµС‚СЊ РіР°Р·РѕРїРѕС‚СЂРµР±Р»РµРЅРёСЏ",
        "name": "РЎРµС‚СЊ РіР°Р·РѕРїРѕС‚СЂРµР±Р»РµРЅРёСЏ",
        "reg_number": "Рђ34-99999-0099",
        "location": "РљР°Р±Р°СЂРґРёРЅРѕ-Р‘Р°Р»РєР°СЂСЃРєР°СЏ Р РµСЃРїСѓР±Р»РёРєР°, Рі. РќР°Р»СЊС‡РёРє",
        "hazard_class": "III",
        "hazardous_substances_info": "РџСЂРёСЂРѕРґРЅС‹Р№ РіР°Р· (РјРµС‚Р°РЅ)",
        "hazard_characteristics_116fz": "РСЃРїРѕР»СЊР·РѕРІР°РЅРёРµ РіРѕСЂСЋС‡РёС… РіР°Р·РѕРІ",
        "total_hazardous_substance_quantity": "0.5",
    },
    "equipment": [
        {"name": "Р“Р РџРЁ 03Р‘Рњ-04-РЈ1", "device_name": "Р“Р РџРЁ 03Р‘Рњ-04-РЈ1", "location": "Р“Р РџРЁ",
         "equipment_type": "Р“Р РџРЁ", "specifications": "Р  СЂР°Р±.=0,6 РњРџР°", "process_codes": "2.1"},
    ],
    "responsible_persons": [{"full_name": "РљСѓРјР°С…РѕРІ Рђ.Рђ.", "position": "Р“РµРЅРµСЂР°Р»СЊРЅС‹Р№ РґРёСЂРµРєС‚РѕСЂ", "phone": "+7 (8662) 45-67-89"}],
    "substances": [{"name": "РњРµС‚Р°РЅ", "quantity_kg": 500}],
    "emergency_services": {},
    "pasf": {"organization_name": "РћРћРћ В«РЎРїР°СЃВ»", "short_name": "В«РЎРїР°СЃВ»", "agreement_date": "15.12.2025"},
    "insurance": {},
    "financial_reserve": {},
    "contractor": {"organization_name": "РћРћРћ В«РЎРїР°СЃВ»", "short_name": "В«РЎРїР°СЃВ»", "agreement_date": "15.12.2025"},
    "questionnaire": {},
    "scenarios": [],
    "equipment_scenario_links": [],
    "equipment_defects": [],
    "injury_history": [],
    "accident_history": [],
}

def main():
    print("=" * 60)
    print("PMLA BASELINE CHECK")
    print("=" * 60)

    # Step 1: map_to_v2_context
    print("\n[1] v2 context...")
    v2_ctx = map_to_v2_context(dict(SOURCE_CTX))
    print(f"    total keys: {len(v2_ctx)}")

    # Check org-derived fields
    for key in ["organization_full_name", "organization_short_name", "inn", "ogrn",
                "legal_address", "phone", "email", "director_full_name", "director_position",
                "director_phone", "main_activity_description"]:
        val = v2_ctx.get(key, "")
        status = "вњ“" if val else "вњ—"
        print(f"    {status} {key}: {str(val)[:60]}")

    # Step 2: Render DOCX
    print("\n[2] Rendering DOCX...")
    renderer = PmlaOoxmlFlatRenderer()
    tpl_ph = renderer._extract_flat_placeholders()
    missing = sorted(tpl_ph - set(v2_ctx.keys()))
    if missing:
        print(f"    Auto-filling {len(missing)} placeholders...")
        for k in missing:
            v2_ctx[k] = f"[{k}]"

    out_path = str(FILES_DIR / "pmla_v2_baseline_check.docx")
    renderer.render_to_file(v2_ctx, out_path)
    size = os.path.getsize(out_path)

    # Step 3: Validate DOCX
    import zipfile, re
    with zipfile.ZipFile(out_path, 'r') as zf:
        all_text = ""
        for n in zf.namelist():
            if n.endswith('.xml') or n.endswith('.rels'):
                try:
                    all_text += zf.read(n).decode('utf-8', errors='ignore')
                except:
                    pass
        leftovers = sorted(set(re.findall(r'\{\{|\}\}|\{%|\%\}', all_text)))

    print(f"    size: {size:,} bytes")
    print(f"    Jinja leftovers: {leftovers}")
    with zipfile.ZipFile(out_path, 'r') as zf_check:
        zip_ok = not bool(zf_check.testzip())
    print(f"    ZIP OK: {zip_ok}")
    print(f"    ZIP OK: {zip_ok}")

    # Save context for comparison
    ctx_path = str(FILES_DIR / "pmla_v2_baseline_context.json")
    with open(ctx_path, 'w', encoding='utf-8') as f:
        json.dump(v2_ctx, f, ensure_ascii=False, indent=2, default=str)
    print(f"    Context saved: {ctx_path}")

    print("\n" + "=" * 60)
    print("BASELINE: " + ("вњ“ PASS" if not leftovers else f"вњ— FAIL ({leftovers})"))
    print("=" * 60)

if __name__ == "__main__":
    main()
