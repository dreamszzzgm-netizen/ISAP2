"""PmlaContextBuilder — builds PmlaGenerationContext from data sources.

This service orchestrates data loading from:
1. Primary DB (organization, facility, equipment, substances, persons)
2. Questionnaire (PASF, scenarios, insurance, resources)
3. Geoservice / emergency services directory

The result is a fully populated PmlaGenerationContext with provenance entries.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from src.application.services.pmla_generation_context import PmlaGenerationContext
from src.application.services.pmla_preflight import run_preflight
from src.infrastructure.database.models import (
    EmergencyRescueUnitModel,
    EmergencyServiceModel,
    EquipmentModel,
    HazardousFacilityModel,
    HazardousSubstanceModel,
    OrganizationModel,
    ResponsiblePersonModel,
)

logger = logging.getLogger(__name__)


class PmlaContextBuilder:
    """Builds PmlaGenerationContext from database and auxiliary sources."""

    def __init__(self, session):
        self.session = session

    async def from_questionnaire(self, questionnaire_service, questionnaire_id: UUID) -> PmlaGenerationContext:
        """Build context from a questionnaire.

        Args:
            questionnaire_service: PmlaQuestionnaireService instance
            questionnaire_id: UUID of the questionnaire

        Returns:
            PmlaGenerationContext with provenance
        """
        raw = await questionnaire_service.build_generation_context(questionnaire_id)
        return self._from_raw_context(raw)

    async def from_facility(
        self,
        facility_id: UUID,
        opo_service=None,
        facility_repo=None,
    ) -> PmlaGenerationContext:
        """Build context directly from facility/OPO data (no questionnaire)."""
        if opo_service:
            try:
                raw = await opo_service.build_generation_context(facility_id)
                return self._from_raw_context(raw)
            except Exception as exc:
                logger.warning("OPO context build failed, fallback to DB: %s", exc)

        # Fallback: load from DB directly
        return await self._from_db_fallback(facility_id)

    async def _from_db_fallback(self, facility_id: UUID) -> PmlaGenerationContext:
        """Build minimal context from database tables directly."""
        from sqlalchemy import select

        facility_result = await self.session.execute(
            select(HazardousFacilityModel).where(HazardousFacilityModel.id == facility_id)
        )
        facility = facility_result.scalar_one_or_none()
        if facility is None:
            raise ValueError(f"ОПО с id {facility_id} не найден")

        org_result = await self.session.execute(
            select(OrganizationModel).where(OrganizationModel.id == facility.organization_id)
        )
        org = org_result.scalar_one_or_none()

        eq_result = await self.session.execute(
            select(EquipmentModel).where(EquipmentModel.hazardous_facility_id == facility_id)
        )
        equipment = list(eq_result.scalars().all())

        sub_result = await self.session.execute(
            select(HazardousSubstanceModel).where(
                HazardousSubstanceModel.hazardous_facility_id == facility_id
            )
        )
        substances = list(sub_result.scalars().all())

        persons_result = await self.session.execute(
            select(ResponsiblePersonModel).where(
                ResponsiblePersonModel.organization_id == facility.organization_id
            )
        )
        persons = list(persons_result.scalars().all())

        ctx = PmlaGenerationContext()

        # Organization
        if org:
            ctx.organization = {
                "id": str(org.id),
                "name": org.name or "",
                "inn": org.inn or "",
                "ogrn": org.ogrn or "",
                "address": org.address or "",
                "phone": org.phone or "",
                "email": org.email or "",
            }
            ctx.add_provenance("organization.name", "organization", str(org.id), "name")
            ctx.add_provenance("organization.inn", "organization", str(org.id), "inn")
            ctx.add_provenance("organization.address", "organization", str(org.id), "address")

        # Facility
        ctx.facility = {
            "id": str(facility.id),
            "name": facility.name or "",
            "reg_number": facility.reg_number or "",
            "hazard_class": facility.hazard_class,
            "facility_type": facility.facility_type or "",
            "address": facility.address or "",
            "latitude": float(facility.latitude) if facility.latitude else None,
            "longitude": float(facility.longitude) if facility.longitude else None,
            "commissioning_date": (
                facility.commissioning_date.isoformat() if facility.commissioning_date else None
            ),
            "inventory_number": facility.inventory_number,
            "properties": facility.properties or {},
        }
        ctx.add_provenance("facility.name", "facility", str(facility.id), "name")
        ctx.add_provenance("facility.reg_number", "facility", str(facility.id), "reg_number")
        ctx.add_provenance("facility.hazard_class", "facility", str(facility.id), "hazard_class")
        ctx.add_provenance("facility.address", "facility", str(facility.id), "address")

        # Equipment
        ctx.equipment = [
            {
                "id": str(item.id),
                "name": item.name or "",
                "equipment_type": item.equipment_type or "",
                "serial_number": item.serial_number or "",
                "manufacturer": item.manufacturer or "",
                "manufacture_year": item.manufacture_year,
                "specifications": item.specifications or {},
            }
            for item in equipment
        ]
        if ctx.equipment:
            ctx.add_provenance("equipment", "equipment", str(facility_id),
                               f"equipment[{len(ctx.equipment)} items]")

        # Substances
        ctx.hazardous_substances = [
            {
                "id": str(item.id),
                "name": item.name or "",
                "cas_number": item.cas_number or "",
                "quantity_kg": float(item.quantity_kg) if item.quantity_kg else 0,
                "threshold_quantity_kg": (
                    float(item.threshold_quantity_kg) if item.threshold_quantity_kg else None
                ),
                "hazard_properties": item.hazard_properties or {},
            }
            for item in substances
        ]
        if ctx.hazardous_substances:
            ctx.add_provenance("hazardous_substances", "substances", str(facility_id),
                               f"substances[{len(ctx.hazardous_substances)} items]")

        # Persons
        ctx.responsible_persons = [
            {
                "id": str(item.id),
                "full_name": item.full_name or "",
                "position": item.position or "",
                "role": item.role or "",
                "phone": item.phone or "",
                "email": item.email or "",
            }
            for item in persons
        ]
        if ctx.responsible_persons:
            ctx.add_provenance("responsible_persons", "responsible_person",
                               str(org.id) if org else "",
                               f"persons[{len(ctx.responsible_persons)} items]")

        return ctx

    def _from_raw_context(self, raw: dict[str, Any]) -> PmlaGenerationContext:
        """Convert a raw context dict (from questionnaire or OPO) to PmlaGenerationContext."""
        ctx = PmlaGenerationContext()
        ctx._raw_source_context = raw

        org = raw.get("organization") or {}
        ctx.organization = dict(org)
        if org.get("id"):
            ctx.add_provenance("organization.name", "organization", str(org["id"]), "name")
            ctx.add_provenance("organization.inn", "organization", str(org["id"]), "inn")
            ctx.add_provenance("organization.address", "organization", str(org["id"]), "address")

        fac = raw.get("facility") or {}
        ctx.facility = dict(fac)
        if fac.get("id"):
            ctx.add_provenance("facility.name", "facility", str(fac["id"]), "name")
            ctx.add_provenance("facility.reg_number", "facility", str(fac["id"]), "reg_number")
            ctx.add_provenance("facility.hazard_class", "facility", str(fac["id"]), "hazard_class")
            ctx.add_provenance("facility.address", "facility", str(fac["id"]), "address")

        # Equipment
        eq = raw.get("equipment") or []
        ctx.equipment = list(eq)
        if eq:
            ctx.add_provenance("equipment", "equipment",
                               str(fac.get("id", "")),
                               f"equipment[{len(eq)} items]")

        # Substances
        subs = raw.get("substances") or []
        ctx.hazardous_substances = list(subs)
        if subs:
            ctx.add_provenance("hazardous_substances", "substances",
                               str(fac.get("id", "")),
                               f"substances[{len(subs)} items]")

        # Persons
        persons = raw.get("responsible_persons") or []
        ctx.responsible_persons = list(persons)
        if persons:
            ctx.add_provenance("responsible_persons", "responsible_person",
                               str(org.get("id", "")),
                               f"persons[{len(persons)} items]")

        # PASF
        pasf = raw.get("pasf") or {}
        ctx.pasf = dict(pasf) if pasf else {}
        if pasf.get("id"):
            ctx.add_provenance("pasf", "pasf", str(pasf["id"]), "name")

        # PASF documents
        pasf_docs = raw.get("pasf_documents") or []
        ctx.attachments = list(pasf_docs)
        for i, doc in enumerate(pasf_docs):
            doc_id = doc.get("id", "")
            if doc_id:
                ctx.add_provenance(
                    f"pasf_documents.{i}",
                    "directory",
                    str(doc_id),
                    "pasf_document",
                )

        # Emergency services
        services = raw.get("emergency_services") or []
        if isinstance(services, list):
            ctx.emergency_services = list(services)
        elif isinstance(services, dict):
            # Flatten grouped services
            flat = []
            for st, items in services.items():
                for item in (items or []):
                    d = dict(item)
                    d.setdefault("service_type", st)
                    flat.append(d)
            ctx.emergency_services = flat

        nearest = raw.get("nearest_services") or {}
        ctx.emergency_services_grouped = dict(nearest)

        if ctx.emergency_services:
            ctx.add_provenance("emergency_services", "questionnaire",
                               str(raw.get("questionnaire", {}).get("id", "")),
                               "selected_emergency_service_ids")

        # Questionnaire data
        qdata = raw.get("questionnaire") or {}
        ctx.questionnaire = dict(qdata)

        # Financial reserve
        fin = qdata.get("financial_reserve") or raw.get("financial_reserve") or {}
        ctx.financial_reserve = dict(fin)

        fin_insurance = (
            qdata.get("financial_reserve_insurance")
            or raw.get("financial_reserve_insurance")
            or fin.get("insurance")
            or {}
        )
        ctx.financial_reserve_insurance = dict(fin_insurance)

        # Insurance
        ins = qdata.get("insurance") or raw.get("insurance") or {}
        ctx.insurance = dict(ins)

        # Organization resources
        resources = qdata.get("organization_resources") or raw.get("organization_resources") or {}
        ctx.organization_resources = dict(resources) if isinstance(resources, dict) else {}

        # Scenarios
        ctx.selected_scenarios = list(raw.get("selected_scenarios") or [])
        ctx.custom_scenarios = list(raw.get("custom_scenarios") or [])

        # Notification scheme
        ctx.notification_scheme = dict(qdata.get("notification_scheme") or {})

        # Training
        ctx.training = dict(qdata.get("training") or {})

        # Accidents
        incident = qdata.get("incident_history") or raw.get("incident_history") or {}
        ctx.accident_history = dict(incident) if isinstance(incident, dict) else {}

        # Attachments checklist (plain list of strings from the questionnaire, e.g.
        # ["схема расположения ОПО", "договор с ПАСФ", ...]) is NOT the same as
        # ctx.attachments (PASF document dicts). Keep it in the questionnaire dict
        # and the raw source so downstream consumers (enhanced_generator,
        # quality_review, v2 mapper) can read it via context["attachments_checklist"]
        # without overwriting the PASF document list the preflight validates.
        attachments_checklist = qdata.get("attachments_checklist") or raw.get("attachments_checklist") or []
        ctx.questionnaire.setdefault("attachments_checklist", attachments_checklist)
        ctx._raw_source_context.setdefault("attachments_checklist", attachments_checklist)

        # Recommendations from questionnaire service
        recommendations = raw.get("recommendations") or {}
        ctx.recommendations = dict(recommendations) if isinstance(recommendations, dict) else {}

        return ctx

    def build_and_check(
        self,
        ctx: PmlaGenerationContext,
        generation_mode: str = "final",
    ) -> tuple[PmlaGenerationContext, Any]:
        """Build preflight report and check if generation should proceed.

        Args:
            ctx: The generation context
            generation_mode: "draft" or "final"

        Returns:
            Tuple of (context, preflight_report)

        Raises:
            ValueError: If generation is blocked (final mode with blockers)
        """
        ctx.generation_mode = generation_mode
        report = run_preflight(ctx, generation_mode=generation_mode)

        if report.has_blockers:
            ctx.preflight_status = "has_blockers"
            if generation_mode == "final":
                report.raise_if_blocked(generation_mode)
        elif report.has_warnings:
            ctx.preflight_status = "has_warnings"
        else:
            ctx.preflight_status = "passed"

        return ctx, report
