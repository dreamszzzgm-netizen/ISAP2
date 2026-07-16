"""Application service for PMLA generation workflows.

This service keeps long-running/business generation logic out of FastAPI
routers. API handlers should validate HTTP input/output only and delegate
context building, document creation, generator wiring and regeneration here.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select

from src.application.services.enhanced_generator import EnhancedDocumentGenerator
from src.application.services.opo_service import OpoService
from src.infrastructure.database.models import (
    DocumentModel,
    DocumentVersionModel,
    EquipmentModel,
    HazardousFacilityModel,
    HazardousSubstanceModel,
    OrganizationModel,
    ResponsiblePersonModel,
)
from src.infrastructure.llm.providers import get_llm_provider
from src.infrastructure.rag.pipeline import Embedder, Retriever, VectorStore
from src.infrastructure.repositories.document_repo import DocumentRepository
from src.infrastructure.repositories.regulatory_repo import RegulatoryRepository
from src.infrastructure.repositories.scenario_matrix_repo import (
    ScenarioMatrixRepository,
)

logger = logging.getLogger(__name__)


class PmlaGenerationService:
    """Coordinates PMLA generation and partial regeneration."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        regulatory_repo: RegulatoryRepository,
        scenario_matrix_repo: ScenarioMatrixRepository | None = None,
        sample_repo: Any | None = None,
        opo_repo: Any | None = None,
        facility_repo: Any | None = None,
    ) -> None:
        self.document_repo = document_repo
        self.regulatory_repo = regulatory_repo
        self.scenario_matrix_repo = scenario_matrix_repo
        self.sample_repo = sample_repo
        self.opo_repo = opo_repo
        self.facility_repo = facility_repo

    async def generate(
        self,
        facility_id: UUID,
        context: dict | None = None,
        regenerate_sections: list[str] | None = None,
        template_version: str = "v1",
    ) -> dict:
        """Create a new PMLA document and run generation pipeline.

        Args:
            facility_id: OPO facility UUID
            context: Optional pre-built context dict (if None, auto-builds)
            regenerate_sections: Optional list of section IDs to regenerate (v1 only)
            template_version: "v1" (engine-based) or "v2" (DOCX template-based)

        Returns:
            dict with document_id, status, version

        Raises:
            ValueError: if facility not found or v2 context validation fails
        """
        facility = await self._get_facility_or_none(facility_id)
        if facility is None:
            raise ValueError("Объект ОПО не найден")

        generation_context = context or await self.build_context(facility_id)

        if template_version == "v2":
            return await self._generate_v2(facility, generation_context)

        # v1 path: engine-based generation (existing behaviour)
        doc = await self._create_processing_document(facility)
        generator = self._create_generator()
        result = await generator.generate(
            document_id=doc.id,
            context=generation_context,
            regenerate_sections=regenerate_sections,
        )

        return {
            "document_id": str(doc.id),
            "status": result.status,
            "version": result.version_number,
        }

    async def _generate_v2(
        self,
        facility: Any,
        source_context: dict,
    ) -> dict:
        """v2 template-based generation path using PmlaOoxmlFlatRenderer.

        Steps:
        1. Enrich context with runtime data (emergency services, protective eq)
        2. Map to flat v2 schema format
        3. Validate against schema
        4. Create DocumentModel
        5. Render DOCX via PmlaOoxmlFlatRenderer (byte-for-byte OOXML copy;
           preserves graphics, namespaces and relationships of the template)
        6. Save to DB + create version snapshot
        """
        from src.application.services.pmla_ooxml_flat_renderer import PmlaOoxmlFlatRenderer
        from src.application.services.pmla_v2_context_mapper import (
            map_to_v2_context,
            validate_v2_context,
        )

        # 1. Enrich context (same as v1 does before generator)
        await self._enrich_context_with_runtime_data(source_context)

        # 2. Map to v2 format
        v2_context = map_to_v2_context(source_context)

        # 3. Validate against schema
        validation_errors = validate_v2_context(v2_context)
        if validation_errors:
            error_detail = "; ".join(validation_errors[:10])
            raise ValueError(
                f"Контекст v2 не прошёл валидацию ({len(validation_errors)} ошибок): "
                f"{error_detail}"
            )

        # 4. Create document record
        doc = await self._create_processing_document(facility)

        try:
            # 5. Render DOCX via v2 template
            renderer = PmlaOoxmlFlatRenderer()
            docx_bytes = renderer.render(v2_context)

            # 6. Save to DB
            doc.content_docx = docx_bytes
            doc.status = "pending_review"
            doc.generation_meta = {
                "source": "pmla_v2_template",
                "template_version": "v2",
                "generation_pipeline": "pmla_ooxml_flat_renderer",
                "facility_id": str(facility.id),
                "context_keys": list(v2_context.keys()),
            }
            await self.document_repo.session.commit()

            # Create version snapshot
            version = DocumentVersionModel(
                document_id=doc.id,
                version_number=doc.version or 1,
                input_data=v2_context,
                template_version="v2.0",
                content_docx=docx_bytes,
            )
            await self.document_repo.add_version(version)

            return {
                "document_id": str(doc.id),
                "status": doc.status,
                "version": doc.version or 1,
            }

        except Exception as exc:
            # Clean up on failure: mark document as failed
            logger.exception("v2 template generation failed")
            doc.status = "generation_failed"
            existing_meta = dict(doc.generation_meta) if doc.generation_meta else {}
            existing_meta["error"] = str(exc)
            doc.generation_meta = existing_meta
            await self.document_repo.session.commit()
            raise ValueError(f"Ошибка генерации v2: {exc}") from exc

    async def regenerate_sections(self, document_id: UUID, sections: list[str]) -> dict:
        """Regenerate selected sections of an existing PMLA document."""
        doc = await self.document_repo.get(document_id)
        if doc is None:
            raise ValueError("Документ не найден")
        if not doc.hazardous_facility_id:
            raise ValueError("Документ не привязан к объекту ОПО")

        context = await self.build_context(doc.hazardous_facility_id, prefer_opo_context=False)
        generator = self._create_generator()
        result = await generator.generate(
            document_id=document_id,
            context=context,
            regenerate_sections=sections,
        )

        return {
            "document_id": str(result.document_id),
            "status": result.status,
            "version": result.version_number,
            "regenerated_sections": sections,
        }

    async def auto_regenerate_sections(self, document_id: UUID, sections: list[str]) -> None:
        """Best-effort section regeneration used after reviewer rejection."""
        try:
            await self.regenerate_sections(document_id, sections)
        except ValueError:
            return

    async def build_context(self, facility_id: UUID, *, prefer_opo_context: bool = True) -> dict:
        """Build generation context from OPO details or normalized database tables."""
        if prefer_opo_context and self.opo_repo is not None and self.facility_repo is not None:
            try:
                opo_service = OpoService(self.opo_repo, self.facility_repo)
                context = await opo_service.build_generation_context(facility_id)
                logger.info("Контекст собран из сведений ОПО для facility %s", facility_id)
                await self._enrich_context_with_runtime_data(context)
                return context
            except Exception as exc:  # noqa: BLE001 - fallback is expected here
                logger.warning(
                    "Не удалось собрать контекст из ОПО: %s, используется fallback из БД",
                    exc,
                )

        context = await self._build_fallback_context(facility_id)
        await self._enrich_context_with_runtime_data(context)
        return context

    async def _get_facility_or_none(self, facility_id: UUID) -> HazardousFacilityModel | None:
        result = await self.document_repo.session.execute(
            select(HazardousFacilityModel).where(HazardousFacilityModel.id == facility_id)
        )
        return result.scalar_one_or_none()

    async def _build_fallback_context(self, facility_id: UUID) -> dict:
        facility = await self._get_facility_or_none(facility_id)
        if facility is None:
            raise ValueError("ОПО не найден")

        org_result = await self.document_repo.session.execute(
            select(OrganizationModel).where(OrganizationModel.id == facility.organization_id)
        )
        org = org_result.scalar_one_or_none()

        eq_result = await self.document_repo.session.execute(
            select(EquipmentModel).where(EquipmentModel.hazardous_facility_id == facility_id)
        )
        equipment = list(eq_result.scalars().all())

        sub_result = await self.document_repo.session.execute(
            select(HazardousSubstanceModel).where(
                HazardousSubstanceModel.hazardous_facility_id == facility_id
            )
        )
        substances = list(sub_result.scalars().all())

        persons_result = await self.document_repo.session.execute(
            select(ResponsiblePersonModel).where(
                ResponsiblePersonModel.organization_id == facility.organization_id
            )
        )
        persons = list(persons_result.scalars().all())

        return {
            "organization": {
                "name": org.name if org else "",
                "inn": org.inn if org else "",
                "address": org.address if org else "",
                "phone": org.phone if org else "",
                "email": org.email if org else "",
            } if org else {},
            "facility": {
                "name": facility.name,
                "facility_type": facility.facility_type,
                "hazard_class": facility.hazard_class,
                "reg_number": facility.reg_number,
                "address": facility.address,
                "latitude": float(facility.latitude) if facility.latitude else None,
                "longitude": float(facility.longitude) if facility.longitude else None,
                "commissioning_date": (
                    facility.commissioning_date.isoformat()
                    if facility.commissioning_date
                    else None
                ),
                "inventory_number": facility.inventory_number,
            },
            "equipment": [
                {
                    "name": item.name,
                    "equipment_type": item.equipment_type,
                    "serial_number": item.serial_number,
                }
                for item in equipment
            ],
            "substances": [
                {
                    "name": item.name,
                    "quantity_kg": float(item.quantity_kg) if item.quantity_kg else 0,
                    "cas_number": item.cas_number,
                    "hazard_properties": item.hazard_properties or {},
                }
                for item in substances
            ],
            "responsible_persons": [
                {
                    "full_name": person.full_name,
                    "position": person.position,
                    "role": person.role,
                    "phone": person.phone,
                }
                for person in persons
            ],
        }

    async def _create_processing_document(
        self,
        facility: HazardousFacilityModel,
    ) -> DocumentModel:
        doc = DocumentModel(
            hazardous_facility_id=facility.id,
            organization_id=facility.organization_id,
            document_type="pmla",
            title="План мероприятий по локализации и ликвидации последствий аварий",
            status="processing",
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        self.document_repo.session.add(doc)
        await self.document_repo.session.commit()
        await self.document_repo.session.refresh(doc)
        return doc

    async def _enrich_context_with_runtime_data(self, context: dict) -> None:
        await self._add_emergency_services(context)
        self._add_protective_equipment(context)

    async def _add_emergency_services(self, context: dict) -> None:
        lat = context.get("facility", {}).get("latitude")
        lng = context.get("facility", {}).get("longitude")
        if not lat or not lng:
            return

        try:
            from src.infrastructure.references.emergency_services import (
                EmergencyServiceFinder,
            )

            finder = EmergencyServiceFinder()
            emergency = await finder.find_all_nearest(float(lat), float(lng))
            context["emergency_services"] = {
                service_type: [
                    {
                        "name": service.name,
                        "phone": service.phone,
                        "address": service.address,
                        "distance_km": (
                            round(service.distance_km, 1)
                            if service.distance_km
                            else None
                        ),
                    }
                    for service in services
                ]
                for service_type, services in emergency.items()
            }

            forces = []
            for service_type, services in emergency.items():
                for service in services:
                    forces.append(
                        {
                            "scenario_name": f"Привлечение {service_type}",
                            "items": [
                                {
                                    "name": service.name,
                                    "unit": "подразделение",
                                    "quantity": 1,
                                    "location": service.address,
                                },
                            ],
                        }
                    )
            context["forces_calculation"] = forces
        except Exception as exc:  # noqa: BLE001 - external/reference data is optional
            logger.warning("Emergency services enrichment failed: %s", exc)

    def _add_protective_equipment(self, context: dict) -> None:
        protective = []
        for item in context.get("equipment", []):
            eq_type = str(self._field(item, "equipment_type", "") or "").lower()
            if any(kw in eq_type for kw in ["сиз", "огнетушитель", "противогаз", "аптечка", "защит"]):
                protective.append(
                    {
                        "name": self._field(item, "name", ""),
                        "type": self._field(item, "equipment_type", "СИЗ") or "СИЗ",
                        "quantity": 1,
                        "purpose": "Защита персонала",
                    }
                )
        if protective:
            context["protective_equipment"] = protective

    def _create_generator(self) -> EnhancedDocumentGenerator:
        try:
            llm = get_llm_provider()
        except Exception as exc:  # noqa: BLE001 - deterministic generation can continue
            logger.warning("LLM not available: %s", exc)
            llm = None

        try:
            embedder = Embedder()
            vector_store = VectorStore()
            retriever = Retriever(embedder, vector_store)
        except Exception as exc:  # noqa: BLE001 - RAG is optional for deterministic fallback
            logger.warning("RAG/VectorStore not available: %s", exc)
            retriever = None

        return EnhancedDocumentGenerator(
            local_llm=llm,
            external_llm=llm,
            retriever=retriever,
            document_repo=self.document_repo,
            regulatory_repo=self.regulatory_repo,
            scenario_matrix_repo=self.scenario_matrix_repo,
            sample_repo=self.sample_repo,
        )

    @staticmethod
    def _field(item: Any, name: str, default: Any = None) -> Any:
        if isinstance(item, dict):
            return item.get(name, default)
        return getattr(item, name, default)
