"""Load anonymized demo data for PMLA MVP internal validation."""
from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from sqlalchemy import select

from src.application.services.pmla_questionnaire_service import DEFAULT_QUESTIONNAIRE
from src.infrastructure.database.engine import async_session_factory
from src.infrastructure.database.models import (
    EmergencyRescueUnitModel,
    EmergencyServiceModel,
    EquipmentModel,
    HazardousFacilityModel,
    HazardousSubstanceModel,
    OrganizationModel,
    PmlaQuestionnaireModel,
    ResponsiblePersonModel,
)

DATA_FILE = Path(__file__).parent.parent / "data" / "demo_pmla_validation.json"


def _load_data() -> dict[str, Any]:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


async def _one_or_none(session, model, *conditions):
    result = await session.execute(select(model).where(*conditions))
    return result.scalar_one_or_none()


async def load() -> None:
    data = _load_data()
    async with async_session_factory() as session:
        organization = await _upsert_organization(session, data["organization"])
        await _upsert_responsible_persons(
            session,
            organization.id,
            data["responsible_persons"],
        )
        facility = await _upsert_facility(
            session,
            organization.id,
            data["facility"],
        )
        await _upsert_equipment(session, facility.id, data["equipment"])
        await _upsert_substances(session, facility.id, data["substances"])
        pasf = await _upsert_pasf(session, data["pasf"])
        services = []
        for item in data["emergency_services"]:
            services.append(await _upsert_emergency_service(session, item))
        questionnaire = await _upsert_questionnaire(
            session,
            organization.id,
            facility.id,
            pasf.id,
            [item.id for item in services],
            data["questionnaire"],
        )
        await session.commit()

        print("Demo PMLA validation data loaded.")
        print(f"Organization: {organization.name} ({organization.id})")
        print(f"Facility: {facility.name} ({facility.id})")
        print(f"Questionnaire: {questionnaire.id}")
        print(f"PASF/ASF: {pasf.name} ({pasf.id})")
        print(f"Emergency services: {len(services)}")


async def _upsert_organization(session, item: dict[str, Any]) -> OrganizationModel:
    organization = await _one_or_none(
        session,
        OrganizationModel,
        OrganizationModel.inn == item["inn"],
    )
    if organization is None:
        organization = OrganizationModel(**item)
        session.add(organization)
        await session.flush()
        return organization

    for key, value in item.items():
        setattr(organization, key, value)
    return organization


async def _upsert_responsible_persons(
    session,
    organization_id,
    people: list[dict[str, Any]],
) -> None:
    for item in people:
        person = await _one_or_none(
            session,
            ResponsiblePersonModel,
            ResponsiblePersonModel.organization_id == organization_id,
            ResponsiblePersonModel.role == item["role"],
        )
        payload = {**item, "organization_id": organization_id}
        if person is None:
            session.add(ResponsiblePersonModel(**payload))
            continue
        for key, value in payload.items():
            setattr(person, key, value)


async def _upsert_facility(
    session,
    organization_id,
    item: dict[str, Any],
) -> HazardousFacilityModel:
    facility = await _one_or_none(
        session,
        HazardousFacilityModel,
        HazardousFacilityModel.reg_number == item["reg_number"],
    )
    payload = {**item, "organization_id": organization_id}
    if facility is None:
        facility = HazardousFacilityModel(**payload)
        session.add(facility)
        await session.flush()
        return facility

    for key, value in payload.items():
        setattr(facility, key, value)
    return facility


async def _upsert_equipment(session, facility_id, items: list[dict[str, Any]]) -> None:
    for item in items:
        equipment = await _one_or_none(
            session,
            EquipmentModel,
            EquipmentModel.hazardous_facility_id == facility_id,
            EquipmentModel.serial_number == item["serial_number"],
        )
        payload = {**item, "hazardous_facility_id": facility_id}
        if equipment is None:
            session.add(EquipmentModel(**payload))
            continue
        for key, value in payload.items():
            setattr(equipment, key, value)


async def _upsert_substances(session, facility_id, items: list[dict[str, Any]]) -> None:
    for item in items:
        substance = await _one_or_none(
            session,
            HazardousSubstanceModel,
            HazardousSubstanceModel.hazardous_facility_id == facility_id,
            HazardousSubstanceModel.name == item["name"],
        )
        payload = {**item, "hazardous_facility_id": facility_id}
        if substance is None:
            session.add(HazardousSubstanceModel(**payload))
            continue
        for key, value in payload.items():
            setattr(substance, key, value)


async def _upsert_pasf(session, item: dict[str, Any]) -> EmergencyRescueUnitModel:
    pasf = await _one_or_none(
        session,
        EmergencyRescueUnitModel,
        EmergencyRescueUnitModel.certificate_number == item["certificate_number"],
    )
    if pasf is None:
        pasf = EmergencyRescueUnitModel(**item)
        session.add(pasf)
        await session.flush()
        return pasf

    for key, value in item.items():
        setattr(pasf, key, value)
    return pasf


async def _upsert_emergency_service(
    session,
    item: dict[str, Any],
) -> EmergencyServiceModel:
    service = await _one_or_none(
        session,
        EmergencyServiceModel,
        EmergencyServiceModel.service_type == item["service_type"],
        EmergencyServiceModel.name == item["name"],
    )
    if service is None:
        service = EmergencyServiceModel(**item)
        session.add(service)
        await session.flush()
        return service

    for key, value in item.items():
        setattr(service, key, value)
    return service


async def _upsert_questionnaire(
    session,
    organization_id,
    facility_id,
    pasf_id,
    service_ids,
    questionnaire_data: dict[str, Any],
) -> PmlaQuestionnaireModel:
    questionnaire = await _one_or_none(
        session,
        PmlaQuestionnaireModel,
        PmlaQuestionnaireModel.facility_id == facility_id,
    )
    data = deepcopy(DEFAULT_QUESTIONNAIRE)
    data.update(questionnaire_data)
    data["selected_pasf_id"] = str(pasf_id)
    data["selected_emergency_service_ids"] = [str(item) for item in service_ids]

    payload = {
        "organization_id": organization_id,
        "facility_id": facility_id,
        "title": "Анкета ПМЛА: демо ОПО для internal validation",
        "data": data,
    }
    if questionnaire is None:
        questionnaire = PmlaQuestionnaireModel(**payload)
        session.add(questionnaire)
        await session.flush()
        return questionnaire

    for key, value in payload.items():
        setattr(questionnaire, key, value)
    return questionnaire


if __name__ == "__main__":
    asyncio.run(load())
