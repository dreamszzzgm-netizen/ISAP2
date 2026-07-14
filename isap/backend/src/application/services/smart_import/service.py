"""Smart Import Center service."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.pmla_facility_matching_service import (
    PmlaFacilityMatchingService,
)
from src.application.services.pmla_import_normalizer import PmlaImportNormalizer
from src.application.services.smart_import.parser import SmartImportParser
from src.application.services.smart_import.profiles import IMPORT_PROFILES, ImportProfile
from src.infrastructure.database.models import (
    EmergencyRescueUnitModel,
    EmergencyServiceModel,
    HazardousFacilityModel,
    ImportJobModel,
    ImportRowModel,
    OrganizationModel,
    PmlaQuestionnaireModel,
)
from src.infrastructure.repositories.facility_repo import FacilityRepository
from src.infrastructure.repositories.organization_repo import OrganizationRepository


class SmartImportService:
    """Creates import previews and applies confirmed imports."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.parser = SmartImportParser()

    def list_profiles(self) -> list[dict[str, Any]]:
        return [
            {
                "code": profile.code,
                "title": profile.title,
                "description": profile.description,
                "target_table": profile.target_table,
                "required_fields": profile.required_fields,
                "duplicate_keys": profile.duplicate_keys,
                "fields": [
                    {
                        "canonical": field.canonical,
                        "title": field.title,
                        "required": field.required,
                        "synonyms": field.synonyms,
                    }
                    for field in profile.fields
                ],
            }
            for profile in IMPORT_PROFILES.values()
        ]

    async def create_preview(self, *, import_type: str, filename: str, content: bytes) -> dict[str, Any]:
        profile = self._get_profile(import_type)
        table = self.parser.parse_bytes(filename, content)
        header_mapping = profile.map_headers(table.headers)

        job = ImportJobModel(
            import_type=profile.code,
            filename=filename,
            status="preview",
            header_mapping=header_mapping,
            total_rows=len(table.rows),
        )
        self.session.add(job)
        await self.session.flush()

        created = updated = skipped = error_rows = warning_rows = 0
        preview_rows = []
        for row_number, raw in enumerate(table.rows, start=2):
            normalized = profile.normalize_row(raw, header_mapping)
            errors, warnings = profile.validate_row(normalized)
            duplicates = await self._find_duplicates(profile, normalized)
            status = "valid"
            action = "create"
            if errors:
                status = "invalid"
                action = "skip"
                error_rows += 1
            elif duplicates:
                status = "duplicate"
                action = "update"
                updated += 1
            else:
                created += 1
            if warnings:
                warning_rows += 1

            import_row = ImportRowModel(
                job_id=job.id,
                row_number=row_number,
                raw_data=self._json_safe(raw),
                mapped_data=self._json_safe(normalized),
                normalized_data=self._json_safe(normalized),
                status=status,
                errors=errors,
                warnings=warnings,
                duplicate_candidates=duplicates,
                action=action,
            )
            self.session.add(import_row)
            preview_rows.append(self._row_to_dict(import_row))
            if action == "skip":
                skipped += 1

        job.created_rows = created
        job.updated_rows = updated
        job.skipped_rows = skipped
        job.error_rows = error_rows
        job.warning_rows = warning_rows
        job.report = self._build_report(job)
        await self.session.commit()
        await self.session.refresh(job)

        return {
            "job": self._job_to_dict(job),
            "header_mapping": header_mapping,
            "rows": preview_rows[:100],
        }

    async def get_job(self, job_id: UUID) -> dict[str, Any]:
        job = await self._get_job_model(job_id)
        return self._job_to_dict(job)

    async def get_rows(self, job_id: UUID, *, limit: int = 200, offset: int = 0) -> list[dict[str, Any]]:
        await self._get_job_model(job_id)
        result = await self.session.execute(
            select(ImportRowModel)
            .where(ImportRowModel.job_id == job_id)
            .order_by(ImportRowModel.row_number)
            .offset(offset)
            .limit(limit)
        )
        return [self._row_to_dict(row) for row in result.scalars().all()]

    async def confirm_import(
        self,
        job_id: UUID,
        bind_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        job = await self._get_job_model(job_id)
        if job.status not in {"preview", "confirmed"}:
            raise ValueError(f"Импорт в статусе '{job.status}' нельзя подтвердить")

        profile = self._get_profile(job.import_type)
        result = await self.session.execute(
            select(ImportRowModel)
            .where(ImportRowModel.job_id == job_id)
            .order_by(ImportRowModel.row_number)
        )
        rows = list(result.scalars().all())

        created = updated = skipped = errors = 0
        for row in rows:
            if row.status == "invalid" or row.action == "skip":
                skipped += 1
                continue
            try:
                if profile.code == "fire_departments":
                    outcome = await self._apply_emergency_service(job, row, default_service_type="fire")
                elif profile.code == "emergency_services":
                    service_type = (row.normalized_data or {}).get("service_type", "other")
                    outcome = await self._apply_emergency_service(job, row, default_service_type=service_type)
                elif profile.code == "pasf_units":
                    outcome = await self._apply_pasf_unit(job, row)
                elif profile.code == "pmla_questionnaire":
                    outcome = await self._apply_pmla_questionnaire(job, row, bind_params=bind_params)
                else:
                    raise ValueError(f"Профиль не поддерживается: {profile.code}")
                if outcome == "created":
                    created += 1
                elif outcome == "updated":
                    updated += 1
                row.status = "imported"
                row.action = outcome
            except Exception as exc:  # noqa: BLE001 - row level error report
                row.status = "invalid"
                row.errors = [*list(row.errors or []), str(exc)]
                errors += 1

        job.status = "completed" if errors == 0 else "completed_with_errors"
        job.created_rows = created
        job.updated_rows = updated
        job.skipped_rows = skipped
        job.error_rows = errors
        job.finished_at = datetime.now(UTC).replace(tzinfo=None)
        job.report = self._build_report(job)
        await self.session.commit()
        await self.session.refresh(job)
        return self._job_to_dict(job)

    def _get_profile(self, import_type: str) -> ImportProfile:
        profile = IMPORT_PROFILES.get(import_type)
        if not profile:
            raise ValueError(f"Неизвестный профиль импорта: {import_type}")
        return profile

    async def _get_job_model(self, job_id: UUID) -> ImportJobModel:
        result = await self.session.execute(select(ImportJobModel).where(ImportJobModel.id == job_id))
        job = result.scalar_one_or_none()
        if job is None:
            raise ValueError("Задание импорта не найдено")
        return job

    async def _find_duplicates(self, profile: ImportProfile, row: dict[str, Any]) -> list[dict[str, Any]]:
        if profile.code == "fire_departments":
            return await self._find_emergency_service_duplicates(row, "fire")
        if profile.code == "emergency_services":
            service_type = row.get("service_type", "other")
            return await self._find_emergency_service_duplicates(row, service_type)
        if profile.code == "pasf_units":
            return await self._find_pasf_duplicates(row)
        return []

    async def _find_emergency_service_duplicates(self, row: dict[str, Any], service_type: str) -> list[dict[str, Any]]:
        conditions = [EmergencyServiceModel.service_type == service_type]
        candidates = []
        name = row.get("name")
        address = row.get("address")
        phone = row.get("phone") or row.get("dispatcher_phone")
        if name and address:
            candidates.append(
                (EmergencyServiceModel.name.ilike(f"%{name}%"))
                & (EmergencyServiceModel.address.ilike(f"%{address}%"))
            )
        if phone:
            candidates.append(
                or_(EmergencyServiceModel.phone == phone, EmergencyServiceModel.dispatcher_phone == phone)
            )
        if not candidates:
            return []
        result = await self.session.execute(
            select(EmergencyServiceModel).where(*conditions).where(or_(*candidates)).limit(5)
        )
        return [
            {"id": str(item.id), "name": item.name, "address": item.address, "phone": item.phone}
            for item in result.scalars().all()
        ]

    async def _find_pasf_duplicates(self, row: dict[str, Any]) -> list[dict[str, Any]]:
        candidates = []
        name = row.get("name")
        certificate = row.get("certificate_number")
        if name:
            candidates.append(EmergencyRescueUnitModel.name.ilike(f"%{name}%"))
        if certificate:
            candidates.append(EmergencyRescueUnitModel.certificate_number == certificate)
        if not candidates:
            return []
        result = await self.session.execute(select(EmergencyRescueUnitModel).where(or_(*candidates)).limit(5))
        return [
            {"id": str(item.id), "name": item.name, "certificate_number": item.certificate_number}
            for item in result.scalars().all()
        ]

    async def _apply_emergency_service(self, job: ImportJobModel, row: ImportRowModel, default_service_type: str) -> str:
        data = dict(row.normalized_data or {})
        data.setdefault("service_type", default_service_type)
        data["source_import_job_id"] = job.id
        existing = None
        duplicates = row.duplicate_candidates or []
        if duplicates:
            existing_id = duplicates[0].get("id")
            if existing_id:
                result = await self.session.execute(
                    select(EmergencyServiceModel).where(EmergencyServiceModel.id == UUID(existing_id))
                )
                existing = result.scalar_one_or_none()
        if existing:
            for key, value in data.items():
                if hasattr(existing, key) and value not in (None, ""):
                    setattr(existing, key, value)
            return "updated"
        self.session.add(EmergencyServiceModel(**data))
        return "created"

    async def _apply_pasf_unit(self, job: ImportJobModel, row: ImportRowModel) -> str:
        data = dict(row.normalized_data or {})
        data["source_import_job_id"] = job.id
        existing = None
        duplicates = row.duplicate_candidates or []
        if duplicates:
            existing_id = duplicates[0].get("id")
            if existing_id:
                result = await self.session.execute(
                    select(EmergencyRescueUnitModel).where(EmergencyRescueUnitModel.id == UUID(existing_id))
                )
                existing = result.scalar_one_or_none()
        if existing:
            for key, value in data.items():
                if hasattr(existing, key) and value not in (None, "", []):
                    setattr(existing, key, value)
            return "updated"
        self.session.add(EmergencyRescueUnitModel(**data))
        return "created"

    async def _apply_pmla_questionnaire(
        self,
        job: ImportJobModel,
        row: ImportRowModel,
        bind_params: dict[str, Any] | None = None,
    ) -> str:
        flat_data = dict(row.normalized_data or {})
        result = PmlaImportNormalizer().normalize(flat_data)

        # --- Resolve binding (organisation / facility) ---
        binding = await self._resolve_pmla_binding(
            result.organization_candidate,
            result.facility_candidate,
            bind_params,
        )

        # --- Store binding info in _import_meta ---
        result.questionnaire_data["_import_meta"].update({
            "organization_candidate": result.organization_candidate,
            "facility_candidate": result.facility_candidate,
            "selected_organization_id": str(binding["organization_id"]) if binding["organization_id"] else None,
            "selected_facility_id": str(binding["facility_id"]) if binding["facility_id"] else None,
            "binding_method": binding["binding_method"],
            "requires_binding": binding["requires_binding"],
        })

        title = (
            f"Анкета ПМЛА: {result.organization_candidate.get('name')
            or result.facility_candidate.get('name')
            or job.filename}"
        )

        self.session.add(
            PmlaQuestionnaireModel(
                title=title,
                data=result.questionnaire_data,
                organization_id=binding["organization_id"],
                facility_id=binding["facility_id"],
                source_import_job_id=job.id,
            )
        )
        return "created"

    async def _resolve_pmla_binding(
        self,
        org_candidate: dict[str, Any],
        fac_candidate: dict[str, Any],
        bind_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Resolve organisation / facility binding for a PMLA questionnaire.

        Priority:
        1. Explicit IDs from confirm request (bind_params)
        2. Auto-binding via unique registration number
        3. Fallback — no binding (draft)
        """
        org_id: UUID | None = None
        fac_id: UUID | None = None
        binding_method = "none"
        requires_binding = True
        warnings: list[str] = []

        # --- 1. Explicit IDs ---
        if bind_params:
            provided_org_id = bind_params.get("organization_id")
            provided_fac_id = bind_params.get("facility_id")

            if provided_fac_id:
                # Validate facility exists
                fac_result = await self.session.execute(
                    select(HazardousFacilityModel).where(
                        HazardousFacilityModel.id == UUID(str(provided_fac_id))
                    )
                )
                facility = fac_result.scalar_one_or_none()
                if not facility:
                    raise ValueError(f"ОПО с ID {provided_fac_id} не найден")

                fac_id = facility.id
                org_id = facility.organization_id

                # If organisation also explicitly provided, validate consistency
                if provided_org_id:
                    if UUID(str(provided_org_id)) != facility.organization_id:
                        raise ValueError(
                            f"ОПО {facility.name} принадлежит организации "
                            f"{facility.organization_id}, не {provided_org_id}"
                        )
                    org_id = UUID(str(provided_org_id))

                binding_method = "explicit"
                requires_binding = False
            elif provided_org_id:
                # Validate organisation exists
                org_result = await self.session.execute(
                    select(OrganizationModel).where(
                        OrganizationModel.id == UUID(str(provided_org_id))
                    )
                )
                org = org_result.scalar_one_or_none()
                if not org:
                    raise ValueError(f"Организация с ID {provided_org_id} не найдена")
                org_id = UUID(str(provided_org_id))
                binding_method = "explicit"
                requires_binding = fac_id is None  # still need facility

            return {
                "organization_id": org_id,
                "facility_id": fac_id,
                "binding_method": binding_method,
                "requires_binding": requires_binding,
                "warnings": warnings,
            }

        # --- 2. Auto-binding via matching service ---
        matching = PmlaFacilityMatchingService(
            OrganizationRepository(self.session),
            FacilityRepository(self.session),
        )
        resolution = await matching.resolve_auto_binding(org_candidate, fac_candidate)

        return {
            "organization_id": resolution.organization_id,
            "facility_id": resolution.facility_id,
            "binding_method": resolution.binding_method,
            "requires_binding": resolution.requires_binding,
            "warnings": resolution.warnings,
        }

    @staticmethod
    def _build_report(job: ImportJobModel) -> dict[str, Any]:
        return {
            "total_rows": job.total_rows or 0,
            "created_rows": job.created_rows or 0,
            "updated_rows": job.updated_rows or 0,
            "skipped_rows": job.skipped_rows or 0,
            "error_rows": job.error_rows or 0,
            "warning_rows": job.warning_rows or 0,
        }

    @staticmethod
    def _job_to_dict(job: ImportJobModel) -> dict[str, Any]:
        return {
            "id": str(job.id),
            "import_type": job.import_type,
            "filename": job.filename,
            "status": job.status,
            "header_mapping": job.header_mapping or {},
            "total_rows": job.total_rows or 0,
            "created_rows": job.created_rows or 0,
            "updated_rows": job.updated_rows or 0,
            "skipped_rows": job.skipped_rows or 0,
            "error_rows": job.error_rows or 0,
            "warning_rows": job.warning_rows or 0,
            "report": job.report or {},
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        }

    @staticmethod
    def _row_to_dict(row: ImportRowModel) -> dict[str, Any]:
        return {
            "id": str(row.id) if row.id else None,
            "row_number": row.row_number,
            "raw_data": row.raw_data or {},
            "mapped_data": row.mapped_data or {},
            "normalized_data": row.normalized_data or {},
            "status": row.status,
            "errors": row.errors or [],
            "warnings": row.warnings or [],
            "duplicate_candidates": row.duplicate_candidates or [],
            "action": row.action,
        }

    @staticmethod
    def _json_safe(data: dict[str, Any]) -> dict[str, Any]:
        safe: dict[str, Any] = {}
        for key, value in data.items():
            if hasattr(value, "isoformat"):
                safe[key] = value.isoformat()
            else:
                safe[key] = value
        return safe
