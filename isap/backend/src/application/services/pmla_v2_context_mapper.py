"""PMLA v2 Context Mapper — transforms engine-style context into flat v2 schema format.

This module provides the bridge between the existing nested generation context
(used by EnhancedDocumentGenerator, DataEngine, NarrativeEngine, etc.) and the
flat dict expected by the v2 DOCX template (pmla_v2_template.docx).

Usage:
    context_v2 = map_to_v2_context(source_context)
    errors = validate_v2_context(context_v2)
    if not errors:
        docx_bytes = PmlaTemplateRenderer().render(context_v2)
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Path to the v2 schema file
_SCHEMA_PATH = Path(__file__).resolve().parents[4] / "files" / "pmla_v2.schema.json"
# Fallback for container: /files/pmla_v2.schema.json (mounted from host ./files/)
_CONTAINER_SCHEMA_PATH = Path("/files/pmla_v2.schema.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _roman_hazard_class(hc: Any) -> str:
    """Convert int/str hazard class (1-4) to Roman numeral (I-IV)."""
    roman_map = {1: "I", 2: "II", 3: "III", 4: "IV", "1": "I", "2": "II", "3": "III", "4": "IV"}
    if hc in roman_map:
        return roman_map[hc]
    return str(hc)


def _safe_str(value: Any, default: str = "") -> str:
    """Return string value or default."""
    if value is None:
        return default
    return str(value)


def _format_date_str(value: Any) -> str:
    """Format supported date values as DD.MM.YYYY for the v2 DOCX schema."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().strftime("%d.%m.%Y")
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    raw = str(value).strip()
    if not raw or raw == "—":
        return raw
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d.%m.%Y"):
        try:
            parsed = datetime.strptime(raw[:19], fmt)
            return parsed.strftime("%d.%m.%Y")
        except ValueError:
            continue
    return raw


def _extract_initials_surname(full_name: str) -> str:
    """Convert 'Иванов Иван Иванович' → 'И.И. Иванов'."""
    parts = full_name.strip().split()
    if len(parts) >= 3:
        surname = parts[0]
        initials = "".join(p[0] + "." for p in parts[1:])
        return f"{initials} {surname}"
    if len(parts) == 2:
        return f"{parts[1][0]}. {parts[0]}"
    return full_name


def _parse_settlement(address: str) -> tuple[str, str]:
    """Extract settlement name and district from address.

    Examples:
        'г. Москва, ул. Тестовая, д. 1' → ('г. Москва', '')
        'Московская область, г. Тест' → ('г. Тест', 'Московская область')
    """
    if not address:
        return "", ""
    # Try to find city/town pattern (with word boundary to avoid partial word matches)
    city_match = re.search(r'\b(?:г\.?\s*|город\s+|п\.?\s*|пос\.?\s*|д\.?\s*|с\.?\s*|село\s+|деревня\s+)([А-Яа-яЁё\-\s]+)', address)
    district_match = re.search(r'\b(?:р-н\s*|район\s+|область\s*)([А-Яа-яЁё\-\s]+)', address)
    # First try to get the settlement from the beginning
    settlement = city_match.group(0).strip() if city_match else ""
    # Try to find region/area name
    settlement2 = ""
    if not settlement:
        # Maybe it starts with the city name
        first_part = address.split(",")[0].strip()
        if any(kw in first_part for kw in ["г.", "город", "п.", "пос.", "с.", "д."]):
            settlement = first_part
    district = district_match.group(1).strip() if district_match else ""
    if not district:
        # Try to extract from the first part
        parts = address.split(",")
        if len(parts) > 1:
            region_part = parts[0].strip()
            if any(kw in region_part for kw in ["область", "край", "республика"]):
                district = region_part
    return settlement or address.split(",")[0].strip(), district


def _find_person(persons: list[dict], role: str | None = None) -> dict | None:
    """Find first responsible person matching role, or first person."""
    if role and persons:
        for p in persons:
            if isinstance(p, dict) and p.get("role") == role:
                return p
    return persons[0] if persons else None


# Service type normalization
_SERVICE_TYPE_ALIASES = {
    "fire": {"fire", "fire_department", "fire_service", "пожарная", "пожарная_охрана"},
    "ambulance": {"ambulance", "medical", "medical_service", "скорая", "скорная", "медицинская"},
    "police": {"police", "полиция"},
    "gas": {"gas", "gas_service", "газовая", "газовая_служба"},
    "electric": {"electric", "electricity", "power", "power_service", "электрика", "энергосбыт"},
    "edds": {"edds", "112", "еддс"},
    "mchs": {"mchs", "emergency", "мчс", "чрезвычайные_ситуации"},
    "rostechnadzor": {"rostechnadzor", "rtn", "ростехнадзор"},
    "admin": {"admin", "administration", "администрация", "местная_администрация"},
    "pasf": {"pasf", "пасф", "ппсф", "пфас"},
    "gas_supplier": {"gas_supplier", "газоснабжение", "газопровод"},
}

def _normalize_service_type(service_type: str) -> str:
    """Normalize service type to canonical form."""
    if not service_type:
        return ""
    st = service_type.lower().strip()
    for canonical, aliases in _SERVICE_TYPE_ALIASES.items():
        if st in aliases:
            return canonical
    return st  # Return as-is if no alias matches


def _find_emergency_service_by_type(
    services: dict | list, canonical_type: str,
) -> dict | None:
    """Find first emergency service of given canonical type."""
    canonical_type = _normalize_service_type(canonical_type)
    if isinstance(services, dict):
        for raw_type, raw_items in services.items():
            if _normalize_service_type(str(raw_type)) != canonical_type:
                continue
            items = raw_items if isinstance(raw_items, list) else [raw_items]
            for svc in items:
                if isinstance(svc, dict):
                    return svc
    elif isinstance(services, list):
        for svc in services:
            if isinstance(svc, dict) and _normalize_service_type(svc.get("service_type", "")) == canonical_type:
                return svc
    return None


def _get_phone(service: dict | None, *keys: str) -> str:
    """Get phone from service dict trying multiple keys."""
    if not service:
        return ""
    for key in keys:
        val = service.get(key)
        if val:
            return _safe_str(val)
    return ""


def _find_emergency_service(
    services: dict | list, service_type: str,
) -> dict | None:
    """Find first emergency service of given type (uses normalization)."""
    return _find_emergency_service_by_type(services, service_type)


# ---------------------------------------------------------------------------
# Equipment mapping
# ---------------------------------------------------------------------------

def _map_equipment(source_equipment: list[dict]) -> list[dict]:
    """Map source equipment items to v2 EquipmentItem format."""
    result = []
    for item in source_equipment:
        if not isinstance(item, dict):
            continue
        specs = item.get("specifications") or {}
        if isinstance(specs, dict):
            specs_str = "; ".join(f"{k}: {v}" for k, v in specs.items() if v)
        else:
            specs_str = _safe_str(specs)
        result.append({
            "location": _safe_str(item.get("location") or specs.get("location") or "—"),
            "hazard_characteristic": _safe_str(item.get("equipment_type") or "—"),
            "device_name": _safe_str(item.get("name") or item.get("device_name") or "—"),
            "specifications": specs_str or "—",
            "process_codes": _safe_str(specs.get("process_codes") or item.get("process_codes") or "—"),
        })
    return result


def _map_substance_params(source_substances: list[dict]) -> list[dict]:
    """Map source substances to v2 SubstanceParam array (key-value pairs)."""
    result = []
    for sub in source_substances:
        if not isinstance(sub, dict):
            continue
        name = _safe_str(sub.get("name", ""))
        if not name:
            continue
        result.append({"parameter": "Наименование вещества", "value": name})
        qty = sub.get("quantity_kg")
        if qty is not None:
            result.append({"parameter": "Количество, кг", "value": str(qty)})
        cas = sub.get("cas_number")
        if cas:
            result.append({"parameter": "CAS номер", "value": str(cas)})
        # Hazard properties
        hp = sub.get("hazard_properties") or {}
        if isinstance(hp, dict):
            for k, v in hp.items():
                if v:
                    result.append({"parameter": k.replace("_", " ").capitalize(), "value": str(v)})
    return result


def _map_equipment_scenario_links(
    equipment: list[dict], scenarios: list[dict],
) -> list[dict]:
    """Create equipment-scenario links combining equipment and scenarios."""
    links = []
    for eq in equipment:
        if not isinstance(eq, dict):
            continue
        eq_id = _safe_str(eq.get("id") or eq.get("equipment_id") or "")
        eq_name = _safe_str(eq.get("name") or eq.get("device_name") or "—")
        # Match scenarios relevant to this equipment via equipment_ids
        matching_codes = []
        descriptions = set()
        factors = set()
        for sc in scenarios:
            if not isinstance(sc, dict):
                continue
            # Check if this scenario references this equipment
            sc_equip_ids = sc.get("equipment_ids") or sc.get("equipment_id") or []
            if isinstance(sc_equip_ids, str):
                sc_equip_ids = [sc_equip_ids]
            matches_equipment = bool(eq_id and eq_id in sc_equip_ids)
            # Matrix-selected scenarios often do not carry equipment_ids; keep
            # the previous broad fallback so the v2 table is still informative.
            if not sc_equip_ids:
                matches_equipment = True
            if matches_equipment:
                code = _safe_str(sc.get("code", ""))
                if code:
                    matching_codes.append(code)
                desc = sc.get("description") or sc.get("name", "")
                if desc:
                    descriptions.add(str(desc))
                df = sc.get("damaging_factors")
                if df:
                    if isinstance(df, list):
                        factors.update(str(f) for f in df)
                    else:
                        factors.add(str(df))
        links.append({
            "equipment_name": eq_name,
            "scenario_codes": ", ".join(matching_codes) if matching_codes else "—",
            "description": "; ".join(descriptions) if descriptions else "—",
            "damaging_factors": ", ".join(factors) if factors else "—",
        })
    return links


def _map_accident_scenarios(
    scenarios: list[dict],
    questionnaire_scenarios: list[dict] | None = None,
    custom_scenarios: list[dict] | None = None,
) -> list[dict]:
    """Map scenarios to v2 AccidentScenario format."""
    result = []
    seen_codes: set[str] = set()

    for sc in scenarios:
        if not isinstance(sc, dict):
            continue
        code = _safe_str(sc.get("code") or f"С-{len(result) + 1}")
        if code in seen_codes:
            continue
        seen_codes.add(code)
        damaging = sc.get("damaging_factors") or sc.get("damaging_factors_text") or ""
        if isinstance(damaging, list):
            damaging = ", ".join(str(d) for d in damaging)
        signs = sc.get("signs") or sc.get("signs_list") or ""
        if isinstance(signs, list):
            signs = "; ".join(str(s) for s in signs)
        result.append({
            "code": code,
            "name": _safe_str(sc.get("name") or sc.get("title", "")),
            "source": _safe_str(sc.get("source") or sc.get("source_equipment", "") or "—"),
            "preconditions": _safe_str(sc.get("preconditions") or sc.get("description", "") or "—"),
            "signs": _safe_str(signs) or "—",
            "damaging_factors": _safe_str(damaging) or "—",
        })

    # Add questionnaire/custom scenarios - handle both dict and string formats
    for sc in (questionnaire_scenarios or []) + (custom_scenarios or []):
        if not isinstance(sc, dict):
            # Convert string scenario to dict
            sc_str = _safe_str(sc)
            if not sc_str:
                continue
            sc = {
                "title": sc_str,
                "name": sc_str,
                "description": sc_str,
            }
        code = _safe_str(sc.get("code") or f"С-{len(result) + 1}")
        if code in seen_codes:
            continue
        seen_codes.add(code)
        result.append({
            "code": code,
            "name": _safe_str(sc.get("name") or sc.get("title", "")),
            "source": _safe_str(sc.get("source") or sc.get("source_equipment", "") or "—"),
            "preconditions": _safe_str(sc.get("preconditions") or sc.get("description", "") or "—"),
            "signs": _safe_str(sc.get("signs", "")) or "—",
            "damaging_factors": _safe_str(sc.get("damaging_factors", "")) or "—",
        })

    return result


def _load_countermeasures(facility_type: str | None = None) -> list[dict]:
    """Load countermeasures from reference data for the given facility type."""
    ref_path = Path(__file__).resolve().parents[4] / "backend" / "data" / "references" / "scenario_instructions.json"
    alt_path = Path(__file__).resolve().parents[4] / "data" / "references" / "scenario_instructions.json"

    data = None
    for p in [ref_path, alt_path]:
        if p.exists():
            try:
                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
                break
            except (json.JSONDecodeError, OSError):
                continue

    if not data or not isinstance(data, dict):
        return []

    templates = data.get("templates", {})
    if not facility_type:
        # Return first available
        for ft, scenarios in templates.items():
            return _scenarios_to_countermeasures(scenarios)

    scenarios = templates.get(facility_type, [])
    # Try partial match
    if not scenarios and facility_type:
        for key, sc_list in templates.items():
            if key.lower() in facility_type.lower() or facility_type.lower() in key.lower():
                scenarios = sc_list
                break
    if not scenarios:
        return []

    return _scenarios_to_countermeasures(scenarios)


def _scenarios_to_countermeasures(scenarios: list[dict]) -> list[dict]:
    """Convert scenario_instructions items to Countermeasure format."""
    result = []
    for sc in scenarios:
        if not isinstance(sc, dict):
            continue
        signs = sc.get("signs") or []
        if isinstance(signs, list):
            signs_str = "; ".join(str(s) for s in signs)
        else:
            signs_str = str(signs)
        protection = sc.get("protection") or sc.get("protection_methods") or sc.get("optimal_protection") or []
        if isinstance(protection, list):
            protection_str = "; ".join(str(p) for p in protection)
        else:
            protection_str = str(protection)
        technical = sc.get("technical_means") or []
        if isinstance(technical, list):
            technical_str = "; ".join(str(t) for t in technical)
        else:
            technical_str = str(technical)
        actions = sc.get("personnel_actions") or sc.get("actions") or []
        if isinstance(actions, list):
            actions_str = "; ".join(str(a) for a in actions)
        else:
            actions_str = str(actions)
        result.append({
            "scenario_label": f"{_safe_str(sc.get('code', ''))} {_safe_str(sc.get('name', ''))}".strip(),
            "signs": signs_str or "—",
            "protection": protection_str or "—",
            "technical_means": technical_str or "—",
            "executors": actions_str or "—",
        })
    return result


def _map_incident_history(
    incident_history: dict | list | None,
    accident_type: str = "injury",
) -> list[dict]:
    """Map questionnaire incident_history to v2 IncidentRecord array.

    Args:
        incident_history: From questionnaire or context
        accident_type: "injury" for травматизм, "accident" for аварии
    """
    if not incident_history:
        return []

    items = []
    if isinstance(incident_history, dict):
        items = incident_history.get("items") or []
        has_incidents = incident_history.get("has_incidents")
        if not items and has_incidents in (False, "false", "нет", "no", "0"):
            return []  # No incidents reported
        if not items:
            return []
    elif isinstance(incident_history, list):
        items = incident_history
    else:
        return []

    result = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        result.append({
            "year": item.get("year") or 0,
            "incident_number": str(idx + 1),
            "date": _safe_str(item.get("date") or item.get("incident_date") or "—"),
            "character": _safe_str(item.get("character") or item.get("description") or "—"),
            "trauma": _safe_str(item.get("trauma") or item.get("trauma_description") or "—"),
            "consequences": _safe_str(item.get("consequences") or item.get("consequence") or "—"),
            "measures_percent": _safe_str(item.get("measures_percent") or item.get("measures") or "—"),
        })
    return result


def _map_material_reserve(
    organization_resources: dict | list | None,
    financial_reserve: dict | None = None,
) -> list[dict]:
    """Map organization resources to v2 MaterialReserveItem format with group headers."""
    result = []

    if not organization_resources:
        return result

    if isinstance(organization_resources, dict):
        actual = organization_resources.get("actual_items") or []
        recommended = organization_resources.get("recommended_items") or []

        if actual:
            result.append({"is_group_header": True, "group_name": "Фактические силы и средства"})
            for item in actual:
                if isinstance(item, dict):
                    result.append({
                        "is_group_header": False,
                        "name": _safe_str(item.get("name") or item.get("title", "")),
                        "quantity": _safe_str(item.get("quantity") or "—"),
                        "location": _safe_str(item.get("location") or item.get("storage_place", "—")),
                    })
        if recommended:
            result.append({"is_group_header": True, "group_name": "Рекомендуемые средства"})
            for item in recommended:
                if isinstance(item, dict):
                    result.append({
                        "is_group_header": False,
                        "name": _safe_str(item.get("name") or item.get("title", "")),
                        "quantity": _safe_str(item.get("quantity") or "—"),
                        "location": _safe_str(item.get("location") or item.get("storage_place", "—")),
                    })
    elif isinstance(organization_resources, list):
        for idx, item in enumerate(organization_resources):
            if isinstance(item, dict):
                if item.get("is_group_header"):
                    result.append(item)
                else:
                    result.append({
                        "is_group_header": False,
                        "name": _safe_str(item.get("name") or item.get("title", "")),
                        "quantity": _safe_str(item.get("quantity") or "—"),
                        "location": _safe_str(item.get("location") or "—"),
                    })

    return result


# ---------------------------------------------------------------------------
# Main mapping function
# ---------------------------------------------------------------------------

def map_to_v2_context(source_context: dict) -> dict:
    """Transform nested generation context into flat v2 schema format.

    Args:
        source_context: Context dict from PmlaGenerationService.build_context()
                       or from PmlaQuestionnaireService.build_generation_context()
                       optionally enriched by EnhancedDocumentGenerator._enrich_context()

    Returns:
        Flat dict matching pmla_v2.schema.json structure.
    """
    # Extract sub-sections
    org = source_context.get("organization") or {}
    facility = source_context.get("facility") or {}
    equipment = source_context.get("equipment") or []
    substances = source_context.get("substances") or []
    persons = source_context.get("responsible_persons") or []
    services = source_context.get("emergency_services") or source_context.get("nearest_services") or {}
    scenarios = source_context.get("scenarios") or source_context.get("selected_scenarios") or []
    custom_scenarios = source_context.get("custom_scenarios") or []
    questionnaire = source_context.get("questionnaire") or {}
    pasf = source_context.get("pasf") or {}

    # Main responsible person
    director = _find_person(persons, "director") or _find_person(persons)
    deputy = _find_person(persons, "deputy") or _find_person(persons, "deputy_chairman")

    # Director info
    director_full_name = _safe_str(director.get("full_name", "")) if director else ""
    director_position = _safe_str(director.get("position", "")) if director else ""
    director_position_fullname = f"{director_position} {director_full_name}".strip()

    # Settlement from address
    facility_address = _safe_str(facility.get("address", ""))
    settlement_name, settlement_district = _parse_settlement(facility_address)

    # Hazard class
    hazard_class_raw = facility.get("hazard_class") or ""

    # Total substance quantity
    total_qty = 0.0
    for sub in substances:
        if isinstance(sub, dict):
            try:
                total_qty += float(sub.get("quantity_kg") or 0)
            except (ValueError, TypeError):
                pass

    # Substance info string
    substance_names = []
    for sub in substances:
        if isinstance(sub, dict) and sub.get("name"):
            substance_names.append(str(sub["name"]))
    hazardous_substances_info = "; ".join(substance_names) if substance_names else "—"

    # Hazard characteristics from 116-FZ
    hazard_chars = []
    for sub in substances:
        if isinstance(sub, dict):
            hp = sub.get("hazard_properties") or {}
            if isinstance(hp, dict) and hp.get("characteristics"):
                hazard_chars.append(str(hp["characteristics"]))
    hazard_characteristics_116fz = "; ".join(hazard_chars) if hazard_chars else "—"

    # PASF info
    contractor_name = _safe_str(pasf.get("name") or "")
    contractor_short = _safe_str(pasf.get("short_name") or contractor_name)

    # Contract date/number from PASF document of type "contract"
    contractor_date = "—"
    contractor_number = ""
    pasf_docs = source_context.get("pasf_documents") or []
    for doc in pasf_docs:
        if isinstance(doc, dict) and doc.get("document_type") == "contract":
            if doc.get("issued_at"):
                contractor_date = _format_date_str(doc["issued_at"])
            if doc.get("document_number"):
                contractor_number = _safe_str(doc["document_number"])
            break
    appendices_manifest = source_context.get("appendices_manifest")
    if not appendices_manifest:
        from src.application.services.enhanced_generator import _synthesize_appendices_manifest

        appendices_manifest = _synthesize_appendices_manifest(
            source_context.get("attachments_checklist") or [],
            pasf_docs,
        )

    # Fallback to agreement_date ONLY (not certificate_date)
    if contractor_date == "—":
        contractor_date = _format_date_str(pasf.get("agreement_date")) or "—"
    if not contractor_number:
        contractor_number = _safe_str(pasf.get("certificate_number") or "")

    dislocation_address = _safe_str(pasf.get("actual_address") or org.get("address") or facility_address)

    # Emergency services
    edds = _find_emergency_service(services, "edds")
    fire = _find_emergency_service(services, "fire")
    ambulance = _find_emergency_service(services, "ambulance") or _find_emergency_service(services, "medical")
    gas = _find_emergency_service(services, "gas")
    electric = _find_emergency_service(services, "electric")
    admin = _find_emergency_service(services, "admin")
    pasf_svc = _find_emergency_service(services, "pasf")
    mchs = _find_emergency_service(services, "mchs") or _find_emergency_service(services, "emergency")
    rostechnadzor = _find_emergency_service(services, "rostechnadzor") or _find_emergency_service(services, "rtn")

    # EDDS
    edds_name = _safe_str(edds.get("name", "")) if edds else "—"
    edds_district_val = settlement_district or "—"

    # Electric company
    electric_company = _safe_str(electric.get("name", "")) if electric else "—"

    # Local admin
    local_admin = _safe_str(admin.get("name", "")) if admin else "—"

    # Gas supplier (from org or emergency service)
    gas_supplier = _find_emergency_service(services, "gas_supplier") or gas
    gas_supplier_name = _safe_str(gas_supplier.get("name", "") if gas_supplier else org.get("name", ""))
    gas_supplier_branch = _safe_str(gas_supplier.get("branch", "") if gas_supplier else "")

    # Notification phones
    chairman_phone = _safe_str(director.get("phone", "")) if director else ""

    ctx: dict[str, Any] = {
        # Organization
        "organization_full_name": _safe_str(org.get("name", "")),
        "organization_short_name": _safe_str(org.get("short_name") or org.get("name", "")),
        "legal_address": _safe_str(org.get("address", "")),
        "inn": _safe_str(org.get("inn", "")),
        "ogrn": _safe_str(org.get("ogrn", "")),
        "phone": _safe_str(org.get("phone", "")),
        "email": _safe_str(org.get("email", "")),

        # Director
        "director_position_fullname": director_position_fullname or "—",
        "director_initials_surname": _extract_initials_surname(director_full_name) if director_full_name else "—",
        "director_initials_surname_full": director_full_name or "—",
        "deputy_chairman_fullname": _safe_str(deputy.get("full_name", "")) if deputy else "—",

        # Main activity
        "main_activity_description": _safe_str(
            questionnaire.get("main_activity")
            or (facility.get("properties") or {}).get("okved")
            or "—"
        ),

        # Facility
        "facility_name": _safe_str(facility.get("name", "")),
        "facility_reg_number": _safe_str(facility.get("reg_number", "")),
        "facility_location": _safe_str(facility.get("address", "")),
        "hazard_class": _roman_hazard_class(hazard_class_raw),
        "hazardous_substances_info": hazardous_substances_info,
        "hazard_characteristics_116fz": hazard_characteristics_116fz,
        "total_hazardous_substance_quantity": total_qty,

        # Settlement
        "settlement_name": settlement_name or "—",
        "settlement_district": settlement_district or "—",

        # PASF / Contractor
        "contractor_organization_name": contractor_name or "—",
        "contractor_organization_short_name": contractor_short or "—",
        "contractor_agreement_date": contractor_date,
        "contractor_agreement_number": contractor_number,
        "appendices_manifest": appendices_manifest,
        "gas_supplier_name": gas_supplier_name or "—",
        "gas_supplier_branch": gas_supplier_branch or "—",
        "dislocation_address": dislocation_address or "—",

        # EDDS
        "edds_name": edds_name,
        "edds_district": edds_district_val,

        # Utilities + admin
        "electric_company": electric_company,
        "local_admin": local_admin,

        # Notification phones
        "notification_chairman_phone": chairman_phone,
        "notification_deputy_phone": _safe_str(deputy.get("phone", "")) if deputy else "",
        "notification_edds_phone": _get_phone(edds, "dispatcher_phone", "dispatch_phone", "phone", "additional_phone"),
        "notification_pasf_phone": _get_phone(pasf_svc or pasf, "dispatch_phone", "dispatcher_phone", "phone", "additional_phone"),
        "notification_fire_phone": _get_phone(fire, "dispatcher_phone", "phone", "additional_phone"),
        "notification_ambulance_phone": _get_phone(ambulance, "dispatcher_phone", "phone", "additional_phone"),
        "notification_gas_phone": _get_phone(gas, "dispatcher_phone", "phone", "additional_phone"),
        "notification_electric_phone": _get_phone(electric, "dispatcher_phone", "phone", "additional_phone"),
        "notification_mchs_phone": _get_phone(mchs, "dispatcher_phone", "phone", "additional_phone"),
        "notification_rostechnadzor_phone": _get_phone(rostechnadzor, "phone"),
        "notification_admin_phone": _get_phone(admin, "phone"),

        # Arrays
        "equipment_list": _map_equipment(equipment),
        "substance_params": _map_substance_params(substances),
        "equipment_scenario_links": _map_equipment_scenario_links(equipment, scenarios),
        "accident_scenarios": _map_accident_scenarios(
            scenarios,
            questionnaire.get("selected_scenarios"),
            questionnaire.get("custom_scenarios"),
        ),
        "injury_history": _map_incident_history(
            questionnaire.get("incident_history") or source_context.get("incident_history"),
            "injury",
        ),
        "accident_history": _map_incident_history(
            questionnaire.get("incident_history") or source_context.get("incident_history"),
            "accident",
        ),
        "material_reserve": _map_material_reserve(
            questionnaire.get("organization_resources") or source_context.get("organization_resources"),
            questionnaire.get("financial_reserve"),
        ),
        "countermeasures": _load_countermeasures(facility.get("facility_type")),
    }

    # Clean up any None values
    for key, value in list(ctx.items()):
        if isinstance(value, (list, str)):
            if value is None:
                ctx[key] = [] if isinstance(value, list) else ""
        if isinstance(value, float):
            ctx[key] = value

    return ctx


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_v2_context(context: dict) -> list[str]:
    """Validate a v2 context dict against pmla_v2.schema.json.

    Uses a two-pass approach:
    1. Check required property existence (hard errors)
    2. Run jsonschema validation and classify errors as errors vs warnings

    Returns:
        List of human-readable validation error messages.
        Empty list = context is valid and ready for rendering.
    """
    import jsonschema

    schema_path = _SCHEMA_PATH
    if not schema_path.exists():
        schema_path = _CONTAINER_SCHEMA_PATH
    if not schema_path.exists():
        alt = Path(__file__).resolve().parents[4] / "files" / "pmla_v2.schema.json"
        if alt.exists():
            schema_path = alt

    if not schema_path.exists():
        return [f"Schema file not found at {schema_path}"]

    try:
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return [f"Cannot load schema: {e}"]

    errors: list[str] = []
    required_fields = set(schema.get("required", []))
    properties = schema.get("properties", {})

    # Pass 1: check that all required fields exist and are non-null, non-empty
    for req_field in required_fields:
        if req_field not in context or context[req_field] is None:
            errors.append(f"Отсутствует обязательное поле: {req_field}")
            continue
        val = context[req_field]
        prop = properties.get(req_field, {})
        prop_type = prop.get("type", "")
        if prop_type == "array":
            if not isinstance(val, list):
                errors.append(f"Поле {req_field} должно быть массивом")
            elif len(val) == 0:
                errors.append(f"Поле {req_field} не должно быть пустым")
        elif prop_type == "string":
            if not isinstance(val, str):
                errors.append(f"Поле {req_field} должно быть строкой")
            elif not val.strip() or val.strip() in ("", "—"):
                errors.append(f"Поле {req_field} обязательно для заполнения")
        elif prop_type == "number":
            if val == "" or val is None:
                errors.append(f"Поле {req_field} обязательно для заполнения")

    # Pass 2: jsonschema validation — collect pattern mismatches as warnings
    # for phone/date fields (template handles these with Jinja defaults),
    # but flag other structural errors.
    validator = jsonschema.Draft202012Validator(schema)
    schema_errors = sorted(validator.iter_errors(context), key=lambda e: e.path)

    for ve in schema_errors:
        path = " → ".join(str(p) for p in ve.path) if ve.path else "(root)"
        # Skip pattern mismatches for phone and date fields — the template
        # handles these with Jinja | default() filters
        if ve.validator == "pattern":
            field_name = str(ve.path[-1]) if ve.path else ""
            if "phone" in field_name.lower() or "date" in field_name.lower() or "agreement" in field_name.lower():
                continue  # acceptable — template handles with defaults
        # Skip empty string vs pattern for optional fields not in required
        if ve.validator == "pattern" and ve.path:
            field_name = str(ve.path[-1])
            if field_name not in required_fields:
                continue

        msg = ve.message
        errors.append(f"{path}: {msg}")

    return errors
