"""PmlaGenerationContext — typed generation context with provenance tracking.

This module defines the single source of truth for PMLA generation data.
It separates factual data (from DB/questionnaire) from AI-generated content
and tracks provenance for every significant field.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


@dataclass
class ProvenanceEntry:
    """Provenance record for a single field value.

    Attributes:
        source_type: Type of source (organization, facility, questionnaire,
                     directory, geoservice, etc.)
        source_id: Unique identifier of the source record (UUID or string)
        field: Original field name in the source
        retrieved_at: When the value was retrieved
    """
    source_type: str
    source_id: str
    field: str
    retrieved_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "field": self.field,
        }
        if self.retrieved_at:
            d["retrieved_at"] = self.retrieved_at
        return d


# ---------------------------------------------------------------------------
# Generation context
# ---------------------------------------------------------------------------


@dataclass
class PmlaGenerationContext:
    """Typed generation context for PMLA documents.

    All factual data groups are stored as typed attributes.
    AI-generated content lives separately in ``generated_sections``.
    Provenance tracks the origin of every significant field.

    No field in this model should contain AI-generated or LLM-invented data.
    """

    # ── Organization ───────────────────────────────────────────────────
    organization: dict[str, Any] = field(default_factory=dict)
    # Expected keys: id, name, short_name, inn, ogrn, address, phone, email

    # ── Facility / OPO ─────────────────────────────────────────────────
    facility: dict[str, Any] = field(default_factory=dict)
    # Expected keys: id, name, reg_number, hazard_class, facility_type,
    #                address, latitude, longitude, commissioning_date,
    #                inventory_number

    # ── Questionnaire ──────────────────────────────────────────────────
    questionnaire: dict[str, Any] = field(default_factory=dict)
    # Expected keys: incident_history, operation_mode, selected_scenarios,
    #                custom_scenarios, selected_pasf_id, insurance, etc.

    # ── PASF ───────────────────────────────────────────────────────────
    pasf: dict[str, Any] = field(default_factory=dict)
    # Expected keys: id, name, short_name, dispatch_phone, actual_address,
    #                certificate_number, certificate_date, certificate_valid_until,
    #                permitted_work_types, equipment_passport, staff_count

    # ── Emergency services ─────────────────────────────────────────────
    emergency_services: list[dict[str, Any]] = field(default_factory=list)
    # Each item: service_type, name, phone, address, distance_km
    emergency_services_grouped: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    # ── Insurance ──────────────────────────────────────────────────────
    insurance: dict[str, Any] = field(default_factory=dict)
    # Expected keys: has_contract, company, contract_number, valid_until, amount

    # ── Financial reserve ──────────────────────────────────────────────
    financial_reserve: dict[str, Any] = field(default_factory=dict)
    # Expected keys: created, order_number, order_date, amount

    # ── Organization resources / forces ────────────────────────────────
    organization_resources: dict[str, Any] = field(default_factory=dict)
    # Expected keys: actual_items, recommended_items, user_notes

    # ── Responsible persons ────────────────────────────────────────────
    responsible_persons: list[dict[str, Any]] = field(default_factory=list)
    # Each item: full_name, position, role, phone, email

    # ── Equipment ──────────────────────────────────────────────────────
    equipment: list[dict[str, Any]] = field(default_factory=list)
    # Each item: name, equipment_type, serial_number, manufacturer,
    #            manufacture_year, specifications (dict)

    # ── Hazardous substances ───────────────────────────────────────────
    hazardous_substances: list[dict[str, Any]] = field(default_factory=list)
    # Each item: name, cas_number, quantity_kg, threshold_quantity_kg,
    #            hazard_properties (dict)

    # ── Accident history ───────────────────────────────────────────────
    accident_history: dict[str, Any] = field(default_factory=dict)
    # Expected keys: has_incidents, period, items

    # ── Selected / custom scenarios ────────────────────────────────────
    selected_scenarios: list[dict[str, Any]] = field(default_factory=list)
    custom_scenarios: list[dict[str, Any]] = field(default_factory=list)

    # ── Attachments ────────────────────────────────────────────────────
    attachments: list[dict[str, Any]] = field(default_factory=list)
    # Each item: type, filename, exists, source

    # ── Generated sections (AI content, kept separate) ─────────────────
    generated_sections: dict[str, str] = field(default_factory=dict)

    # ── Provenance ─────────────────────────────────────────────────────
    provenance: dict[str, ProvenanceEntry] = field(default_factory=dict)

    # ── Generation metadata ────────────────────────────────────────────
    generation_mode: str = "final"  # "draft" | "final"
    preflight_status: str | None = None  # "passed" | "has_warnings" | "has_blockers"

    # ── Raw context for backward compat ────────────────────────────────
    _raw_source_context: dict[str, Any] = field(default_factory=dict)

    # ── Recommendation hints (from KG/questionnaire) ───────────────────
    recommendations: dict[str, Any] = field(default_factory=dict)

    # ── Notification scheme ────────────────────────────────────────────
    notification_scheme: dict[str, Any] = field(default_factory=dict)

    # ── Training data ──────────────────────────────────────────────────
    training: dict[str, Any] = field(default_factory=dict)

    def add_provenance(self, field_path: str, source_type: str,
                       source_id: str, field_name: str) -> None:
        """Add a provenance entry for a field path (e.g. 'facility.name')."""
        self.provenance[field_path] = ProvenanceEntry(
            source_type=source_type,
            source_id=source_id,
            field=field_name,
            retrieved_at=datetime.now(UTC).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to flat dict compatible with the existing engine-based pipeline.

        This method maintains backward compatibility with EnhancedDocumentGenerator
        and other consumers that expect a plain dict.
        """
        result: dict[str, Any] = {
            "organization": dict(self.organization),
            "facility": dict(self.facility),
            "equipment": list(self.equipment),
            "substances": list(self.hazardous_substances),
            "responsible_persons": list(self.responsible_persons),
            "pasf": dict(self.pasf) if self.pasf else None,
            "emergency_services": list(self.emergency_services),
            "questionnaire": dict(self.questionnaire) if self.questionnaire else {},
            "selected_scenarios": list(self.selected_scenarios),
            "custom_scenarios": list(self.custom_scenarios),
            "insurance": dict(self.insurance),
            "financial_reserve": dict(self.financial_reserve),
            "organization_resources": dict(self.organization_resources) if self.organization_resources else {},
            "incident_history": dict(self.accident_history) if self.accident_history else {},
            "protective_equipment": [],
            "attachments": list(self.attachments),
            "recommendations": dict(self.recommendations) if self.recommendations else {},
        }
        if self._raw_source_context:
            # Preserve additional keys from raw context for engine compatibility
            for k, v in self._raw_source_context.items():
                if k not in result:
                    result[k] = v
        return result

    def to_v2_dict(self) -> dict[str, Any]:
        """Return the dict expected by map_to_v2_context()."""
        # Build a structure that map_to_v2_context() expects
        base = self.to_dict()
        # Add nearest_services for emergency_services grouping
        nearest: dict[str, list[dict]] = {}
        for svc in self.emergency_services:
            st = svc.get("service_type", "other")
            nearest.setdefault(st, []).append(svc)
        base["nearest_services"] = nearest
        return base

    @property
    def has_provenance(self) -> bool:
        return len(self.provenance) > 0

    @property
    def is_draft(self) -> bool:
        return self.generation_mode == "draft"
