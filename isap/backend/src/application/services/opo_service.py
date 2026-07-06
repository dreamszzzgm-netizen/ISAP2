"""Сервис для формы «Сведения об ОПО»."""
from uuid import UUID

from fastapi import HTTPException

from src.infrastructure.repositories.facility_repo import FacilityRepository
from src.infrastructure.repositories.opo_details_repo import OpoDetailsRepository


class OpoService:
    def __init__(self, opo_repo: OpoDetailsRepository, facility_repo: FacilityRepository):
        self._opo_repo = opo_repo
        self._facility_repo = facility_repo

    async def get_details(self, facility_id: UUID) -> dict:
        facility = await self._facility_repo.get(facility_id)
        if facility is None:
            raise HTTPException(status_code=404, detail="ОПО не найден")

        details = await self._opo_repo.get_by_facility_id(facility_id)

        base = {
            "f1_1": facility.name or "",
            "f1_4": facility.address or "",
            "danger_class": str(facility.hazard_class) if facility.hazard_class else "",
            "facility_type": facility.facility_type or "",
            "reg_number": facility.reg_number or "",
        }

        if details and details.form_data:
            base.update(details.form_data)
            base["_has_details"] = True
        else:
            base["_has_details"] = False

        return base

    async def build_generation_context(self, facility_id: UUID) -> dict:
        """
        Собирает полный контекст для генерации ПМЛА из сведений ОПО.

        Маппит поля формы (f1_*, composition, processes, classification)
        на формат, ожидаемый движками генерации.
        """
        facility = await self._facility_repo.get(facility_id)
        if facility is None:
            raise HTTPException(status_code=404, detail="ОПО не найден")

        details = await self._opo_repo.get_by_facility_id(facility_id)
        fd = details.form_data if details and details.form_data else {}

        # === Организация (из f8_*) ===
        org = {}
        if fd.get("applicant_type") == "ip":
            org = {
                "name": fd.get("f8_2_1", ""),
                "inn": fd.get("f8_2_2", ""),
                "ogrn": fd.get("f8_2_3", ""),
                "address": fd.get("f8_2_4", ""),
                "phone": fd.get("f9_5", ""),
                "email": fd.get("f9_6", ""),
            }
        else:
            org = {
                "name": fd.get("f8_1_1", ""),
                "inn": fd.get("f8_1_3", ""),
                "ogrn": fd.get("f8_1_5", ""),
                "address": fd.get("f8_1_6", ""),
                "phone": fd.get("f9_5", ""),
                "email": fd.get("f9_6", ""),
            }

        # === Объект ОПО (из f1_*) ===
        fac = {
            "name": fd.get("f1_1", "") or facility.name or "",
            "facility_type": fd.get("f1_2", "") or facility.facility_type or "",
            "hazard_class": fd.get("danger_class", "") or str(facility.hazard_class) if facility.hazard_class else "",
            "reg_number": fd.get("f1_3", "") or facility.reg_number or "",
            "address": fd.get("f1_4", "") or facility.address or "",
            "latitude": float(facility.latitude) if facility.latitude else fd.get("f1_5_lat"),
            "longitude": float(facility.longitude) if facility.longitude else fd.get("f1_5_lng"),
            "commissioning_date": (
                fd.get("f1_6")
                or (facility.commissioning_date.isoformat() if facility.commissioning_date else None)
            ),
            "inventory_number": fd.get("f1_7_1", "") or facility.inventory_number or "",
        }

        # === Оборудование (из composition) ===
        equipment = []
        for row in fd.get("composition", []):
            equipment.append({
                "name": row.get("name", ""),
                "equipment_type": row.get("substance", ""),
                "serial_number": "",
                "manufacture_year": None,
                "hazard_value": row.get("danger", ""),
                "characteristics": row.get("characteristics", ""),
                "processes": row.get("processes", ""),
            })

        # === Вещества (из composition, где substance заполнено) ===
        substances = []
        for row in fd.get("composition", []):
            substance_name = row.get("substance", "")
            if substance_name:
                substances.append({
                    "name": substance_name,
                    "quantity_kg": 0,
                    "cas_number": "",
                    "hazard_properties": {
                        "danger_value": row.get("danger", ""),
                        "characteristics": row.get("characteristics", ""),
                        "processes": row.get("processes", ""),
                    },
                })

        # === Процессы (типы аварий) ===
        processes = fd.get("processes_text", "")

        # === Классификация опасностей ===
        classification = fd.get("classification_text", "")

        # === Сведения о заявителе ===
        applicant = {
            "type": fd.get("applicant_type", "legal"),
            "f7_total": fd.get("f7", ""),
            "sign_dolj": fd.get("signDolj", ""),
            "sign_podp": fd.get("signPodp", ""),
            "sign_date": fd.get("signDate", ""),
            "sign_mp": fd.get("signMp", ""),
        }

        return {
            "organization": org,
            "facility": fac,
            "equipment": equipment,
            "substances": substances,
            "responsible_persons": [],
            "opo_details": {
                "processes": processes,
                "classification": classification,
                "licenses": fd.get("licenses_text", ""),
                "applicant": applicant,
            },
        }

    async def save_details(self, facility_id: UUID, data: dict) -> dict:
        facility = await self._facility_repo.get(facility_id)
        if facility is None:
            raise HTTPException(status_code=404, detail="ОПО не найден")

        errors = self._validate(data)
        if errors:
            raise HTTPException(status_code=400, detail={"errors": errors})

        applicant_type = data.get("applicant_type", "legal")
        total = self._calc_total(data.get("composition", []))

        await self._opo_repo.upsert(facility_id, {
            "form_data": data,
            "total_amount": total,
            "applicant_type": applicant_type,
        })

        return {"status": "ok", "total_amount": total}

    def _validate(self, data: dict) -> list[str]:
        errors = []
        if not data.get("f1_1", "").strip():
            errors.append("Полное наименование ОПО обязательно")
        if not data.get("f1_4", "").strip():
            errors.append("Адрес ОПО обязателен")
        if not data.get("danger_class", "").strip():
            errors.append("Класс опасности обязателен")
        if not data.get("composition"):
            errors.append("Таблица состава должна содержать хотя бы одну строку")

        applicant_type = data.get("applicant_type", "legal")
        if applicant_type == "legal":
            inn = data.get("f8_1_3", "")
            if inn and (len(inn) != 10 or not inn.isdigit()):
                errors.append("ИНН юрлица должен содержать ровно 10 цифр")
        else:
            inn = data.get("f8_2_2", "")
            if inn and (len(inn) != 12 or not inn.isdigit()):
                errors.append("ИНН ИП должен содержать ровно 12 цифр")

        return errors

    def _calc_total(self, composition: list) -> float:
        total = 0
        for item in composition:
            try:
                total += float(item.get("danger", 0) or 0)
            except (ValueError, TypeError):
                pass
        return round(total, 3)
