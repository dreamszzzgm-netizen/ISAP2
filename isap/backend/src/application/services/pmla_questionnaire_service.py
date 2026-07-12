"""PMLA Questionnaire Builder service."""
from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import (
    EmergencyRescueUnitModel,
    EmergencyServiceModel,
    EquipmentModel,
    HazardousFacilityModel,
    HazardousSubstanceModel,
    OrganizationModel,
    PasfDocumentModel,
    PmlaQuestionnaireModel,
    ResponsiblePersonModel,
)

DEFAULT_QUESTIONNAIRE: dict[str, Any] = {
    "incident_history": {
        "has_incidents": None,
        "period": "за период эксплуатации",
        "items": [],
    },
    "operation_mode": {
        "mode": "",
        "shifts": None,
        "staff_per_shift": None,
        "night_shift": None,
        "has_dispatcher": None,
    },
    "selected_scenarios": [],
    "custom_scenarios": [],
    "selected_pasf_id": None,
    "selected_pasf_document_ids": [],
    "selected_emergency_service_ids": [],
    "organization_resources": {
        "actual_items": [],
        "recommended_items": [],
        "user_notes": "",
    },
    "notification_scheme": {
        "first_receiver": "",
        "responsible_manager": "",
        "calls_pasf": "",
        "calls_fire": "",
        "meets_services": "",
        "contacts": [],
    },
    "training": {
        "conducted": None,
        "frequency": "",
        "last_date": "",
        "last_topic": "",
        "participants": "",
    },
    "financial_reserve": {
        "created": None,
        "order_number": "",
        "order_date": "",
        "amount": "",
    },
    "insurance": {
        "has_contract": None,
        "company": "",
        "contract_number": "",
        "valid_until": "",
    },
    "attachments_checklist": [],
    "source_notes": [],
}


class PmlaQuestionnaireService:
    """Manages questionnaire state and builds generation context."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_for_facility(self, facility_id: UUID) -> dict[str, Any]:
        facility = await self._get_facility(facility_id)
        existing = await self._find_by_facility(facility_id)
        if existing:
            return self._to_dict(existing)
        questionnaire = PmlaQuestionnaireModel(
            organization_id=facility.organization_id,
            facility_id=facility.id,
            title=f"Анкета ПМЛА: {facility.name}",
            data=deepcopy(DEFAULT_QUESTIONNAIRE),
        )
        self.session.add(questionnaire)
        await self.session.commit()
        await self.session.refresh(questionnaire)
        return self._to_dict(questionnaire)

    async def get_by_id(self, questionnaire_id: UUID) -> dict[str, Any]:
        return self._to_dict(await self._get_questionnaire(questionnaire_id))

    async def get_by_facility(self, facility_id: UUID) -> dict[str, Any]:
        questionnaire = await self._find_by_facility(facility_id)
        if not questionnaire:
            return await self.create_for_facility(facility_id)
        return self._to_dict(questionnaire)

    async def update_block(self, questionnaire_id: UUID, block: str, payload: Any) -> dict[str, Any]:
        questionnaire = await self._get_questionnaire(questionnaire_id)
        data = deepcopy(DEFAULT_QUESTIONNAIRE)
        data.update(questionnaire.data or {})
        data[block] = payload
        questionnaire.data = data
        await self.session.commit()
        await self.session.refresh(questionnaire)
        return self._to_dict(questionnaire)

    async def add_custom_scenario(self, questionnaire_id: UUID, scenario: dict[str, Any]) -> dict[str, Any]:
        questionnaire = await self._get_questionnaire(questionnaire_id)
        data = deepcopy(DEFAULT_QUESTIONNAIRE)
        data.update(questionnaire.data or {})
        scenarios = list(data.get("custom_scenarios") or [])
        scenarios.append(scenario)
        data["custom_scenarios"] = scenarios
        questionnaire.data = data
        await self.session.commit()
        await self.session.refresh(questionnaire)
        return self._to_dict(questionnaire)

    async def remove_custom_scenario(self, questionnaire_id: UUID, index: int) -> dict[str, Any]:
        questionnaire = await self._get_questionnaire(questionnaire_id)
        data = deepcopy(DEFAULT_QUESTIONNAIRE)
        data.update(questionnaire.data or {})
        scenarios = list(data.get("custom_scenarios") or [])
        if index < 0 or index >= len(scenarios):
            raise ValueError("Сценарий не найден")
        scenarios.pop(index)
        data["custom_scenarios"] = scenarios
        questionnaire.data = data
        await self.session.commit()
        await self.session.refresh(questionnaire)
        return self._to_dict(questionnaire)

    async def build_generation_context(self, questionnaire_id: UUID) -> dict[str, Any]:
        questionnaire = await self._get_questionnaire(questionnaire_id)
        if not questionnaire.facility_id:
            return {"questionnaire": questionnaire.data or {}, "warnings": ["Анкета не привязана к ОПО"]}

        facility = await self._get_facility(questionnaire.facility_id)
        organization = await self._get_organization(facility.organization_id)
        equipment = await self._get_equipment(facility.id)
        substances = await self._get_substances(facility.id)
        persons = await self._get_persons(organization.id)
        qdata = deepcopy(DEFAULT_QUESTIONNAIRE)
        qdata.update(questionnaire.data or {})

        pasf = None
        if qdata.get("selected_pasf_id"):
            pasf = await self._get_pasf(UUID(str(qdata["selected_pasf_id"])))
        if not pasf and qdata.get("pasf_manual"):
            manual_pasf = dict(qdata.get("pasf_manual") or {})
            pasf = {
                "id": str(qdata.get("selected_pasf_id") or "manual"),
                "name": manual_pasf.get("name"),
                "dispatch_phone": manual_pasf.get("phone"),
                "actual_address": manual_pasf.get("address"),
                "certificate_number": manual_pasf.get("certificate_number"),
                "permitted_work_types": manual_pasf.get("permitted_work_types") or manual_pasf.get("equipment") or [],
                "source": "questionnaire_manual",
            }

        # Load PASF documents
        pasf_documents = []
        if qdata.get("selected_pasf_document_ids"):
            pasf_documents = await self._get_pasf_documents(
                qdata["selected_pasf_document_ids"]
            )

        emergency_services = await self._get_emergency_services(qdata.get("selected_emergency_service_ids") or [])
        manual_services = qdata.get("selected_emergency_services") or []
        if isinstance(manual_services, list):
            emergency_services.extend([item for item in manual_services if isinstance(item, dict)])
        recommendations = self._build_resource_recommendations(facility, substances, qdata)

        return {
            "organization": {
                "id": str(organization.id),
                "name": organization.name,
                "inn": organization.inn,
                "ogrn": organization.ogrn,
                "address": organization.address,
                "phone": organization.phone,
                "email": organization.email,
            },
            "facility": {
                "id": str(facility.id),
                "name": facility.name,
                "reg_number": facility.reg_number,
                "hazard_class": facility.hazard_class,
                "facility_type": facility.facility_type,
                "object_type": facility.facility_type,
                "address": facility.address,
                "latitude": float(facility.latitude) if facility.latitude is not None else None,
                "longitude": float(facility.longitude) if facility.longitude is not None else None,
                "inventory_number": facility.inventory_number,
            },
            "equipment": equipment,
            "substances": substances,
            "responsible_persons": persons,
            "questionnaire": qdata,
            "incident_history": qdata.get("incident_history"),
            "selected_scenarios": qdata.get("selected_scenarios") or [],
            "custom_scenarios": qdata.get("custom_scenarios") or [],
            "pasf": pasf,
            "pasf_documents": pasf_documents,
            "nearest_services": self._group_services(emergency_services),
            "emergency_services": emergency_services,
            "organization_resources": qdata.get("organization_resources"),
            "recommendations": recommendations,
        }

    async def _get_facility(self, facility_id: UUID) -> HazardousFacilityModel:
        result = await self.session.execute(select(HazardousFacilityModel).where(HazardousFacilityModel.id == facility_id))
        facility = result.scalar_one_or_none()
        if not facility:
            raise ValueError("ОПО не найден")
        return facility

    async def _get_organization(self, organization_id: UUID) -> OrganizationModel:
        result = await self.session.execute(select(OrganizationModel).where(OrganizationModel.id == organization_id))
        organization = result.scalar_one_or_none()
        if not organization:
            raise ValueError("Организация не найдена")
        return organization

    async def _find_by_facility(self, facility_id: UUID) -> PmlaQuestionnaireModel | None:
        result = await self.session.execute(select(PmlaQuestionnaireModel).where(PmlaQuestionnaireModel.facility_id == facility_id).order_by(PmlaQuestionnaireModel.updated_at.desc()))
        return result.scalars().first()

    async def _get_questionnaire(self, questionnaire_id: UUID) -> PmlaQuestionnaireModel:
        result = await self.session.execute(select(PmlaQuestionnaireModel).where(PmlaQuestionnaireModel.id == questionnaire_id))
        questionnaire = result.scalar_one_or_none()
        if not questionnaire:
            raise ValueError("Анкета ПМЛА не найдена")
        return questionnaire

    async def _get_equipment(self, facility_id: UUID) -> list[dict[str, Any]]:
        result = await self.session.execute(select(EquipmentModel).where(EquipmentModel.hazardous_facility_id == facility_id))
        return [
            {
                "id": str(item.id),
                "name": item.name,
                "equipment_type": item.equipment_type,
                "serial_number": item.serial_number,
                "manufacturer": item.manufacturer,
                "manufacture_year": item.manufacture_year,
                "specifications": item.specifications or {},
            }
            for item in result.scalars().all()
        ]

    async def _get_substances(self, facility_id: UUID) -> list[dict[str, Any]]:
        result = await self.session.execute(select(HazardousSubstanceModel).where(HazardousSubstanceModel.hazardous_facility_id == facility_id))
        return [
            {
                "id": str(item.id),
                "name": item.name,
                "cas_number": item.cas_number,
                "quantity_kg": float(item.quantity_kg) if item.quantity_kg is not None else None,
                "threshold_quantity_kg": float(item.threshold_quantity_kg) if item.threshold_quantity_kg is not None else None,
                "hazard_properties": item.hazard_properties or {},
            }
            for item in result.scalars().all()
        ]

    async def _get_persons(self, organization_id: UUID) -> list[dict[str, Any]]:
        result = await self.session.execute(select(ResponsiblePersonModel).where(ResponsiblePersonModel.organization_id == organization_id))
        return [
            {
                "id": str(item.id),
                "full_name": item.full_name,
                "position": item.position,
                "role": item.role,
                "phone": item.phone,
                "email": item.email,
            }
            for item in result.scalars().all()
        ]

    async def _get_pasf(self, pasf_id: UUID) -> dict[str, Any] | None:
        result = await self.session.execute(select(EmergencyRescueUnitModel).where(EmergencyRescueUnitModel.id == pasf_id))
        item = result.scalar_one_or_none()
        if not item:
            return None
        return {
            "id": str(item.id),
            "name": item.name,
            "short_name": item.short_name,
            "organization_type": item.organization_type,
            "director_name": item.director_name,
            "director_position": item.director_position,
            "actual_address": item.actual_address,
            "dispatch_phone": item.dispatch_phone,
            "email": item.email,
            "manager_name": item.manager_name,
            "certificate_number": item.certificate_number,
            "certificate_date": item.certificate_date,
            "certificate_valid_until": item.certificate_valid_until,
            "permitted_work_types": item.permitted_work_types or [],
            "equipment_passport": item.equipment_passport or [],
            "staff_count": item.staff_count,
            "readiness_mode": item.readiness_mode,
            "service_area": item.service_area,
            "region": item.region,
            "is_active": bool(item.is_active) if item.is_active is not None else True,
        }

    async def _get_emergency_services(self, service_ids: list[Any]) -> list[dict[str, Any]]:
        if not service_ids:
            return []
        ids = [UUID(str(item)) for item in service_ids]
        result = await self.session.execute(select(EmergencyServiceModel).where(EmergencyServiceModel.id.in_(ids)))
        return [
            {
                "id": str(item.id),
                "service_type": item.service_type,
                "name": item.name,
                "address": item.address,
                "phone": item.phone,
                "dispatcher_phone": item.dispatcher_phone,
                "additional_phone": item.additional_phone,
                "municipality": item.municipality,
                "settlement": item.settlement,
                "latitude": item.latitude,
                "longitude": item.longitude,
                "service_area": item.service_area,
                "region": item.region,
                "is_active": bool(item.is_active) if item.is_active is not None else True,
                "verified_at": item.verified_at,
            }
            for item in result.scalars().all()
        ]

    async def _get_pasf_documents(self, document_ids: list[Any]) -> list[dict[str, Any]]:
        if not document_ids:
            return []
        ids = [UUID(str(item)) for item in document_ids]
        result = await self.session.execute(
            select(PasfDocumentModel).where(PasfDocumentModel.id.in_(ids))
        )
        return [
            {
                "id": str(item.id),
                "pasf_id": str(item.pasf_id),
                "document_type": item.document_type,
                "document_number": item.document_number,
                "title": item.title,
                "issued_at": item.issued_at.isoformat() if item.issued_at else None,
                "valid_until": item.valid_until.isoformat() if item.valid_until else None,
                "file_path": item.file_path,
                "file_name": item.file_name,
                "file_size": item.file_size,
                "mime_type": item.mime_type,
                "checksum_sha256": item.checksum_sha256,
                "status": item.status or "active",
                "verified_at": item.verified_at.isoformat() if item.verified_at else None,
                "verified_by": item.verified_by,
            }
            for item in result.scalars().all()
        ]

    def _build_resource_recommendations(self, facility: HazardousFacilityModel, substances: list[dict[str, Any]], qdata: dict[str, Any]) -> dict[str, Any]:
        facility_type = (facility.facility_type or "").lower()
        substance_text = " ".join(item.get("name", "") for item in substances).lower()
        scenario_text = " ".join(str(item) for item in [*qdata.get("selected_scenarios", []), *qdata.get("custom_scenarios", [])]).lower()
        recommended: list[dict[str, str]] = []
        if "газ" in facility_type or "газ" in substance_text or "метан" in substance_text:
            recommended.extend([
                {"name": "Переносной газоанализатор", "reason": "Контроль загазованности при утечке газа"},
                {"name": "СИЗОД / противогазы", "reason": "Защита органов дыхания персонала"},
                {"name": "Комплект инструмента для перекрытия запорной арматуры", "reason": "Локализация поступления газа"},
                {"name": "Первичные средства пожаротушения", "reason": "Локализация возгорания до прибытия пожарной охраны"},
            ])
        if "пожар" in scenario_text or "воспламен" in scenario_text:
            recommended.append({"name": "Пожарные рукава / огнетушители по месту", "reason": "Сценарии связаны с пожаром или воспламенением"})
        return {
            "resources": recommended,
            "missing_data": self._missing_questionnaire_data(qdata),
            "risk_notes": [],
        }

    @staticmethod
    def _missing_questionnaire_data(qdata: dict[str, Any]) -> list[str]:
        missing = []
        incident = qdata.get("incident_history") or {}
        if incident.get("has_incidents") is None:
            missing.append("Не заполнены сведения об авариях и инцидентах")
        if not qdata.get("selected_pasf_id"):
            missing.append("Не выбран ПАСФ / АСФ")
        if not qdata.get("selected_emergency_service_ids"):
            missing.append("Не выбраны аварийные службы")
        if not qdata.get("selected_scenarios") and not qdata.get("custom_scenarios"):
            missing.append("Не подтверждены сценарии аварий")
        return missing

    @staticmethod
    def _group_services(services: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for service in services:
            grouped.setdefault(service.get("service_type") or "other", []).append(service)
        return grouped

    @staticmethod
    def _to_dict(questionnaire: PmlaQuestionnaireModel) -> dict[str, Any]:
        data = deepcopy(DEFAULT_QUESTIONNAIRE)
        data.update(questionnaire.data or {})
        return {
            "id": str(questionnaire.id),
            "organization_id": str(questionnaire.organization_id) if questionnaire.organization_id else None,
            "facility_id": str(questionnaire.facility_id) if questionnaire.facility_id else None,
            "title": questionnaire.title,
            "data": data,
            "source_import_job_id": str(questionnaire.source_import_job_id) if questionnaire.source_import_job_id else None,
            "created_at": questionnaire.created_at.isoformat() if questionnaire.created_at else None,
            "updated_at": questionnaire.updated_at.isoformat() if questionnaire.updated_at else None,
        }
