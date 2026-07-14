"""PmlaImportNormalizer — transforms flat Smart Import data into structured questionnaire.

The normalizer bridges the gap between the flat key-value format produced by
Smart Import's ``pmla_questionnaire`` profile and the structured ``DEFAULT_QUESTIONNAIRE``
format expected by the downstream generation pipeline.

Usage::

    normalizer = PmlaImportNormalizer()
    result = normalizer.normalize(flat_data)
    # result.questionnaire_data -> structured dict ready for PmlaQuestionnaireModel.data
    # result.organization_candidate -> {"name": ...}
    # result.facility_candidate -> {"name": ..., "reg_number": ...}
    # result.unmapped_fields -> keys not recognised by the normalizer
    # result.warnings -> list of human-readable warnings
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping

from src.application.services.pmla_questionnaire_service import DEFAULT_QUESTIONNAIRE

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TRUE_VALUES = {"да", "есть", "true", "1"}
_FALSE_VALUES = {"нет", "отсутствует", "false", "0"}
_NULL_VALUES = {"", "-", "не указано", "н/д", "none"}

_BOOLEAN_AMBIGUOUS_WARNING = (
    "Не удалось однозначно преобразовать значение '{value}' поля '{field}' "
    "в boolean. Сохранено как None, проверьте данные."
)

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class PmlaImportNormalizationResult:
    """Result of normalising a flat Smart Import row.

    Attributes:
        questionnaire_data: Structured dict conforming to ``DEFAULT_QUESTIONNAIRE``
            structure, enriched with a ``_import_meta`` metadata block.
        organization_candidate: Extracted organisation name (if present).
        facility_candidate: Extracted facility name and reg_number (if present).
        unmapped_fields: Input keys that were not recognised by the normalizer.
        warnings: Human-readable warnings collected during normalisation.
    """
    questionnaire_data: dict[str, Any]
    organization_candidate: dict[str, str] = field(default_factory=dict)
    facility_candidate: dict[str, str] = field(default_factory=dict)
    unmapped_fields: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Safe type converters
# ---------------------------------------------------------------------------


def _to_bool(value: Any, field_name: str, warnings: list[str]) -> bool | None:
    """Convert a string value to bool safely.

    Returns ``True``, ``False``, or ``None`` (when empty or ambiguous).
    Appends a warning for ambiguous values.
    """
    if value is None:
        return None
    raw = str(value).strip().lower()
    if raw in _NULL_VALUES:
        return None
    if raw in _TRUE_VALUES:
        return True
    if raw in _FALSE_VALUES:
        return False
    # Ambiguous — warn and return None
    warnings.append(
        _BOOLEAN_AMBIGUOUS_WARNING.format(value=value, field=field_name)
    )
    return None


def _to_int(value: Any, field_name: str, warnings: list[str]) -> int | None:
    """Convert a value to int safely.

    Returns ``None`` and appends a warning when conversion fails.
    """
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        warnings.append(
            f"Не удалось преобразовать значение '{value}' поля '{field_name}' "
            f"в число. Сохранено как None."
        )
        return None


def _ensure_list(value: Any) -> list[str]:
    """Return value as a list of strings.

    If ``value`` is already a list, normalise its items to strings.
    If it is a string, split by newline or semicolon.
    Otherwise return an empty list.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    # Split by newline or semicolon (common separators in imported data)
    parts = re.split(r"[\n;]+", text)
    return [part.strip(" •-•\t") for part in parts if part.strip(" •-•\t")]


def _split_incident_description(text: str) -> list[dict[str, str]]:
    """Split incident description into structured items.

    We deliberately avoid fabricating complex structure. Each paragraph or
    line break becomes a separate ``{"description": ..., "date": "", "type": ""}``
    entry. This gives downstream consumers clean text blocks without guessing
    dates or types.
    """
    if not text or not str(text).strip():
        return []
    paragraphs = re.split(r"\n\s*\n", str(text).strip())
    return [
        {"description": p.strip(), "date": "", "type": ""}
        for p in paragraphs
        if p.strip()
    ]


# ---------------------------------------------------------------------------
# Normalizer
# ---------------------------------------------------------------------------


class PmlaImportNormalizer:
    """Transforms flat Smart Import data into a structured questionnaire dict.

    The normaliser produces a deep copy of ``DEFAULT_QUESTIONNAIRE``, populates
    its fields from the flat input, and collects metadata, unmapped fields and
    warnings in a separate result envelope.
    """

    # Mapping: flat key -> (target path list, converter, purpose)
    _FIELD_MAP: dict[str, tuple[list[str], str, str]] = {
        # Organisation / facility candidates (stored separately + in _import_meta)
        "organization_name": (["_import_meta", "organization_name"], "str", "org"),
        "facility_name": (["_import_meta", "facility_name"], "str", "facility"),
        "facility_reg_number": (["_import_meta", "facility_reg_number"], "str", "facility"),
        # Incident history
        "has_incidents": (["incident_history", "has_incidents"], "bool", "questionnaire"),
        "incident_description": (["incident_history", "items"], "incident_items", "questionnaire"),
        # Operation mode
        "operation_mode": (["operation_mode", "mode"], "str", "questionnaire"),
        "staff_per_shift": (["operation_mode", "staff_per_shift"], "int", "questionnaire"),
        "night_shift": (["operation_mode", "night_shift"], "bool", "questionnaire"),
        "has_dispatcher": (["operation_mode", "has_dispatcher"], "bool", "questionnaire"),
        # Scenarios
        "selected_scenarios": (["selected_scenarios"], "list", "questionnaire"),
        "custom_scenarios": (["custom_scenarios"], "list", "questionnaire"),
        # Resources
        "resources": (["organization_resources", "actual_items"], "resource_items", "questionnaire"),
        # PASF
        "pasf_name": (["_import_meta", "pasf_name"], "str", "questionnaire"),
        # Financial reserve
        "financial_reserve": (["financial_reserve", "amount"], "str", "questionnaire"),
        # Training
        "training": (["training", "conducted"], "bool", "questionnaire"),
        # Insurance
        "has_insurance": (["insurance", "has_contract"], "bool", "questionnaire"),
        "insurance_company": (["insurance", "company"], "str", "questionnaire"),
        "insurance_contract": (["insurance", "contract_number"], "str", "questionnaire"),
        "insurance_valid_until": (["insurance", "valid_until"], "str", "questionnaire"),
        # Attachments
        "attachments": (["attachments_checklist"], "list", "questionnaire"),
        # Notification scheme
        "notification_first_receiver": (["notification_scheme", "first_receiver"], "str", "questionnaire"),
        "notification_responsible_manager": (["notification_scheme", "responsible_manager"], "str", "questionnaire"),
        "notification_calls_pasf": (["notification_scheme", "calls_pasf"], "str", "questionnaire"),
        "notification_calls_fire": (["notification_scheme", "calls_fire"], "str", "questionnaire"),
        "notification_meets_services": (["notification_scheme", "meets_services"], "str", "questionnaire"),
    }

    # Keys that are stored only in _import_meta and returned as candidates
    _ORG_KEYS = {"organization_name"}
    _FACILITY_KEYS = {"facility_name", "facility_reg_number"}

    def normalize(self, flat_data: Mapping[str, Any]) -> PmlaImportNormalizationResult:
        """Normalise flat Smart Import data into a structured questionnaire.

        Args:
            flat_data: Dictionary of key-value pairs produced by the
                ``pmla_questionnaire`` import profile (from
                ``row.normalized_data``).

        Returns:
            A ``PmlaImportNormalizationResult`` with the structured data,
            candidate records, unmapped fields, and warnings.
        """
        warnings: list[str] = []
        # 1. Deep copy of DEFAULT_QUESTIONNAIRE — guards against mutation
        questionnaire = deepcopy(DEFAULT_QUESTIONNAIRE)
        # 2. Build _import_meta block
        import_meta: dict[str, Any] = {
            "profile": "pmla_questionnaire",
            "normalizer_version": 1,
            "raw_data": dict(flat_data),  # independent copy
            "unmapped_fields": {},
            "warnings": [],
        }

        organisation_candidate: dict[str, str] = {}
        facility_candidate: dict[str, str] = {}
        unmapped: dict[str, Any] = {}

        # 3. Process each input key
        for key, value in flat_data.items():
            if key not in self._FIELD_MAP:
                unmapped[key] = value
                continue

            target_path, converter, purpose = self._FIELD_MAP[key]
            converted = self._convert(value, converter, key, warnings)

            # If the value is None after conversion and the field is optional,
            # we keep None in the questionnaire (DEFAULT_QUESTIONNAIRE already
            # has None for most optional fields).
            if converter == "str" and converted is None:
                converted = ""

            # Set value in questionnaire (navigate target path)
            d = questionnaire
            for part in target_path[:-1]:
                d = d.setdefault(part, {})
            d[target_path[-1]] = converted

            # Also record in _import_meta
            meta_d = import_meta
            for part in target_path[:-1]:
                meta_d = meta_d.setdefault(part, {})
            meta_d[target_path[-1]] = converted

            # Extract organisation / facility candidates
            if key in self._ORG_KEYS and converted:
                organisation_candidate["name"] = str(converted)
            if key == "facility_name" and converted:
                facility_candidate["name"] = str(converted)
            if key == "facility_reg_number" and converted:
                facility_candidate["reg_number"] = str(converted)

        # 4. Finalise metadata — add candidates as readable dicts
        import_meta["unmapped_fields"] = dict(unmapped)
        import_meta["warnings"] = list(warnings)
        import_meta["organization_candidate"] = dict(organisation_candidate)
        import_meta["facility_candidate"] = dict(facility_candidate)
        questionnaire["_import_meta"] = import_meta

        return PmlaImportNormalizationResult(
            questionnaire_data=questionnaire,
            organization_candidate=organisation_candidate,
            facility_candidate=facility_candidate,
            unmapped_fields=unmapped,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Internal: value conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _convert(
        value: Any,
        converter: str,
        field_name: str,
        warnings: list[str],
    ) -> Any:
        """Convert a single value according to the converter name."""
        if converter == "str":
            if value is None:
                return None
            return str(value).strip()
        if converter == "bool":
            return _to_bool(value, field_name, warnings)
        if converter == "int":
            return _to_int(value, field_name, warnings)
        if converter == "list":
            return _ensure_list(value)
        if converter == "incident_items":
            # Convert incident description to a list of structured items
            # without fabricating dates/types
            text = str(value).strip() if value else ""
            if not text:
                return []
            return _split_incident_description(text)
        if converter == "resource_items":
            # Convert a list of resource names to a list of dicts
            items = _ensure_list(value)
            return [{"name": item, "quantity": "", "unit": ""} for item in items]
        # fallback
        return value
