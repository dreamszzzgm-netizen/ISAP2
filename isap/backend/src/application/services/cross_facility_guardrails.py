"""Cross-facility guardrails for PMLA generation.

Prevents content from one facility type from appearing in documents
for a different facility type. This catches cases where fallback logic
or RAG/KG returns facility-inappropriate content.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Facility type normalization aliases
FACILITY_TYPE_ALIASES: dict[str, str] = {
    "сеть газопотребления": "сеть газопотребления",
    "котельная": "котельная",
    "компрессорная станция": "компрессорная станция",
    "азс": "азс",
    "агзс": "агзс",
    "станция газозаправочная автомобильная": "агзс",
    "автомобильная газозаправочная станция": "агзс",
    "газозаправочная станция": "агзс",
}


def normalize_facility_type(facility_type: str) -> str:
    """Normalize facility type to canonical internal key."""
    lower = facility_type.lower().strip()
    for alias, canonical in FACILITY_TYPE_ALIASES.items():
        if alias in lower or lower in alias:
            return canonical
    return lower


# Forbidden terms per facility type.
# If these terms appear in generated text for a facility type, it's contamination.
# NOTE: some terms like "газопровод" may be legitimate for gas-consuming facilities
# (котельная with gas supply, АГЗС with pipelines), so we only block clearly wrong terms.
CROSS_FACILITY_FORBIDDEN: dict[str, list[str]] = {
    "котельная": [
        "ГРПШ",
        "ШРП",
        "газорегуляторный пункт",
        "газорегуляторн",
    ],
    "компрессорная станция": [
        "ГРПШ",
        "ШРП",
        "водогрейный котёл",
        "котёл",
        "горелк",
    ],
    "азс": [
        "ГРПШ",
        "ШРП",
        "водогрейный котёл",
        "котёл",
    ],
    "агзс": [
        "водогрейный котёл",
        "котельная",
        "теплосеть",
        "ГРПШ",
        "ШРП",
    ],
}

# Generic terms that are ALWAYS allowed (safe for any facility type)
SAFE_TERMS = {
    "газопровод",
    "газ",
    "газоснабжение",
    "пожар",
    "авария",
    "эвакуация",
    "оповещение",
    "пожарная охрана",
    "скорая помощь",
}


def check_cross_facility_contamination(
    text: str,
    facility_type: str,
    context_equipment: list[dict] | None = None,
) -> list[str]:
    """Check if text contains terms forbidden for the given facility type.

    Args:
        text: Generated text to check.
        facility_type: Current facility type (will be normalized).
        context_equipment: Equipment list from context (to exclude legit terms).

    Returns:
        List of forbidden terms found (empty = clean).
    """
    if not facility_type:
        return []

    normalized = normalize_facility_type(facility_type)
    forbidden = []
    for ftype, terms in CROSS_FACILITY_FORBIDDEN.items():
        if ftype in normalized or normalized in ftype:
            forbidden = terms
            break

    if not forbidden:
        return []

    # Build set of equipment names from context for exclusion
    equipment_names = set()
    if context_equipment:
        for eq in context_equipment:
            if isinstance(eq, dict):
                name = (eq.get("name") or "").lower()
                if name:
                    equipment_names.add(name)

    found = []
    for term in forbidden:
        # Check if term appears in text
        if term.lower() in text.lower():
            # Check if it's in equipment context (legitimate use)
            term_lower = term.lower()
            in_equipment = any(term_lower in en for en in equipment_names)
            if not in_equipment:
                found.append(term)

    return found
