"""Generate PMLA documents from an engineering questionnaire.

This service is the bridge between the new PMLA questionnaire and the existing
EnhancedDocumentGenerator. The goal is to make generation consume confirmed
engineering facts instead of a loose ad-hoc context.
"""
from __future__ import annotations

import json
import logging
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from src.application.services.enhanced_generator import EnhancedDocumentGenerator
from src.application.services.pmla_questionnaire_service import PmlaQuestionnaireService
from src.infrastructure.database.models import DocumentModel
from src.infrastructure.llm.providers import get_llm_provider
from src.infrastructure.rag.pipeline import Embedder, Retriever, VectorStore
from src.infrastructure.repositories.document_repo import DocumentRepository
from src.infrastructure.repositories.regulatory_repo import RegulatoryRepository
from src.infrastructure.repositories.scenario_matrix_repo import ScenarioMatrixRepository

logger = logging.getLogger(__name__)

QUESTIONNAIRE_DEBUG_DIR = Path(tempfile.gettempdir()) / "isap_pmla_questionnaire_generation"


@dataclass(frozen=True)
class QuestionnaireGenerationResult:
    document_id: UUID
    status: str
    version: int
    questionnaire_id: UUID
    facility_id: UUID
    context_quality: dict[str, Any]
    debug_artifacts: dict[str, str] | None = None


class PmlaGenerationFromQuestionnaireService:
    """Coordinates PMLA generation from questionnaire data."""

    def __init__(
        self,
        *,
        document_repo: DocumentRepository,
        regulatory_repo: RegulatoryRepository,
        scenario_matrix_repo: ScenarioMatrixRepository | None = None,
        sample_repo=None,
    ) -> None:
        self.document_repo = document_repo
        self.regulatory_repo = regulatory_repo
        self.scenario_matrix_repo = scenario_matrix_repo
        self.sample_repo = sample_repo
        self.questionnaires = PmlaQuestionnaireService(document_repo.session)

    async def generate(
        self,
        *,
        questionnaire_id: UUID,
        regenerate_sections: list[str] | None = None,
        save_debug_artifacts: bool = True,
    ) -> QuestionnaireGenerationResult:
        """Generate a PMLA document using questionnaire-derived context."""
        context = await self.questionnaires.build_generation_context(questionnaire_id)
        context = self.adapt_context_for_generator(context)
        quality = self.validate_questionnaire_context(context)

        facility = context.get("facility") or {}
        organization = context.get("organization") or {}
        facility_id = UUID(str(facility.get("id")))
        organization_id = UUID(str(organization.get("id")))

        doc = DocumentModel(
            hazardous_facility_id=facility_id,
            organization_id=organization_id,
            document_type="pmla",
            title="План мероприятий по локализации и ликвидации последствий аварий",
            status="processing",
            generation_meta={
                "source": "pmla_questionnaire",
                "questionnaire_id": str(questionnaire_id),
                "context_quality": quality,
                "created_from_questionnaire_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
            },
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        self.document_repo.session.add(doc)
        await self.document_repo.session.commit()
        await self.document_repo.session.refresh(doc)

        generator = EnhancedDocumentGenerator(
            local_llm=self._safe_llm(),
            external_llm=self._safe_llm(),
            retriever=self._safe_retriever(),
            document_repo=self.document_repo,
            regulatory_repo=self.regulatory_repo,
            scenario_matrix_repo=self.scenario_matrix_repo,
            sample_repo=self.sample_repo,
        )

        generated = await generator.generate(
            document_id=doc.id,
            context=context,
            regenerate_sections=regenerate_sections,
        )

        # Merge questionnaire metadata after EnhancedDocumentGenerator writes its
        # own metadata. This also commits the generated document version.
        fresh_doc = await self.document_repo.get(doc.id)
        generation_meta = dict(fresh_doc.generation_meta or {}) if fresh_doc else {}
        generation_meta.update(
            {
                "source": "pmla_questionnaire",
                "questionnaire_id": str(questionnaire_id),
                "context_quality": quality,
                "context_snapshot": context,
            }
        )
        await self.document_repo.update(doc.id, {"generation_meta": generation_meta})
        fresh_doc = await self.document_repo.get(doc.id)

        artifacts = None
        if save_debug_artifacts:
            artifacts = self._save_debug_artifacts(
                questionnaire_id=questionnaire_id,
                document_id=doc.id,
                context=context,
                quality=quality,
                document=fresh_doc,
            )

        return QuestionnaireGenerationResult(
            document_id=doc.id,
            status=generated.status,
            version=generated.version_number,
            questionnaire_id=questionnaire_id,
            facility_id=facility_id,
            context_quality=quality,
            debug_artifacts=artifacts,
        )

    def adapt_context_for_generator(self, context: dict[str, Any]) -> dict[str, Any]:
        """Normalize questionnaire context into the shape expected by engines."""
        ctx = dict(context)
        questionnaire = ctx.get("questionnaire") or {}

        # Incident history should be explicit for DataEngine/NarrativeEngine.
        incident_history = questionnaire.get("incident_history") or ctx.get("incident_history") or {}
        ctx["incident_history"] = incident_history
        ctx["accidents_and_incidents"] = self._incident_items_or_statement(incident_history)

        # Custom and selected scenarios must participate in generation together
        # with matrix-selected scenarios.
        selected = questionnaire.get("selected_scenarios") or ctx.get("selected_scenarios") or []
        custom = questionnaire.get("custom_scenarios") or ctx.get("custom_scenarios") or []
        ctx["selected_scenarios"] = selected
        ctx["custom_scenarios"] = custom
        ctx["user_scenarios"] = self._normalize_scenarios(selected, custom)

        # Flatten grouped services into the list used by DocumentContext.
        emergency_services = ctx.get("emergency_services") or []
        if isinstance(emergency_services, dict):
            flat: list[dict[str, Any]] = []
            for service_type, items in emergency_services.items():
                for item in items or []:
                    normalized = dict(item)
                    normalized.setdefault("service_type", service_type)
                    flat.append(normalized)
            emergency_services = flat
        ctx["emergency_services"] = emergency_services

        # Add PASF to emergency services so tables and actions can use it.
        pasf = ctx.get("pasf")
        if pasf:
            pasf_service = {
                "service_type": "pasf",
                "name": pasf.get("name"),
                "phone": pasf.get("dispatch_phone"),
                "address": pasf.get("actual_address"),
                "certificate_number": pasf.get("certificate_number"),
                "permitted_work_types": pasf.get("permitted_work_types") or [],
            }
            ctx["emergency_services"] = [pasf_service, *ctx["emergency_services"]]

        # Financial reserve and insurance are rendered by several engines under
        # material_reserve/context_params names.
        financial = questionnaire.get("financial_reserve") or {}
        insurance = questionnaire.get("insurance") or {}
        ctx["material_reserve"] = {
            "fin_reserve_order": self._join_order(financial),
            "fin_reserve_amount": financial.get("amount") or "—",
            "insurance_company": insurance.get("company") or "—",
            "insurance_contract": insurance.get("contract_number") or "—",
            "insurance_valid_until": insurance.get("valid_until") or "—",
        }
        ctx["context_params"] = {
            "fin_reserve_order": ctx["material_reserve"]["fin_reserve_order"],
            "fin_reserve_amount": ctx["material_reserve"]["fin_reserve_amount"],
            "insurance_company": ctx["material_reserve"]["insurance_company"],
        }

        # Organization resources become protective equipment and resource rows.
        resources = questionnaire.get("organization_resources") or ctx.get("organization_resources") or {}
        actual_items = resources.get("actual_items") if isinstance(resources, dict) else []
        ctx["protective_equipment"] = self._normalize_resources(actual_items or [])
        ctx["organization_resources"] = resources
        ctx["notification_scheme"] = questionnaire.get("notification_scheme") or {}

        # Training and attachments are factual questionnaire sections, preserved
        # for narrative sections and context snapshots.
        ctx["training"] = questionnaire.get("training") or {}
        ctx["attachments_checklist"] = questionnaire.get("attachments_checklist") or []
        ctx["recommendations"] = ctx.get("recommendations") or {}
        return ctx

    def validate_questionnaire_context(self, context: dict[str, Any]) -> dict[str, Any]:
        """Soft validation: generation is allowed, but warnings are visible."""
        warnings: list[str] = []
        errors: list[str] = []
        required = {
            "organization.name": (context.get("organization") or {}).get("name"),
            "facility.name": (context.get("facility") or {}).get("name"),
            "facility.facility_type": (context.get("facility") or {}).get("facility_type"),
            "facility.hazard_class": (context.get("facility") or {}).get("hazard_class"),
            "substances": context.get("substances"),
            "equipment": context.get("equipment"),
        }
        for field, value in required.items():
            if not value:
                errors.append(f"Не заполнено обязательное поле: {field}")

        questionnaire = context.get("questionnaire") or {}
        incident = questionnaire.get("incident_history") or {}
        if incident.get("has_incidents") is None:
            warnings.append("Не заполнен блок аварий/инцидентов")
        if not context.get("pasf"):
            warnings.append("Не выбран ПАСФ / АСФ")
        if not context.get("emergency_services"):
            warnings.append("Не выбраны аварийные службы")
        if not context.get("selected_scenarios") and not context.get("custom_scenarios"):
            warnings.append("Не подтверждены сценарии аварий")
        if not context.get("protective_equipment"):
            warnings.append("Не заполнены фактические силы и средства организации")

        return {
            "passed": not errors,
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "error_count": len(errors),
                "warning_count": len(warnings),
                "selected_scenarios": len(context.get("selected_scenarios") or []),
                "custom_scenarios": len(context.get("custom_scenarios") or []),
                "emergency_services": len(context.get("emergency_services") or []),
                "protective_equipment": len(context.get("protective_equipment") or []),
            },
        }

    def _safe_llm(self):
        try:
            return get_llm_provider()
        except Exception as exc:  # noqa: BLE001 - generation can work deterministically
            logger.warning("LLM not available for questionnaire generation: %s", exc)
            return None

    def _safe_retriever(self):
        try:
            return Retriever(Embedder(), VectorStore())
        except Exception as exc:  # noqa: BLE001 - RAG is optional
            logger.warning("RAG not available for questionnaire generation: %s", exc)
            return None

    def _save_debug_artifacts(
        self,
        *,
        questionnaire_id: UUID,
        document_id: UUID,
        context: dict[str, Any],
        quality: dict[str, Any],
        document: DocumentModel | None,
    ) -> dict[str, str]:
        package_dir = QUESTIONNAIRE_DEBUG_DIR / f"{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{document_id.hex[:8]}"
        package_dir.mkdir(parents=True, exist_ok=True)
        context_path = package_dir / "context.json"
        quality_path = package_dir / "context_quality.json"
        meta_path = package_dir / "generation_meta.json"
        rendered_sections_path = package_dir / "rendered_sections.json"
        docx_path = package_dir / "output.docx"
        context_path.write_text(json.dumps(context, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        quality_path.write_text(json.dumps(quality, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        meta_path.write_text(
            json.dumps(
                {
                    "questionnaire_id": str(questionnaire_id),
                    "document_id": str(document_id),
                    "status": document.status if document else None,
                    "generation_meta": document.generation_meta if document else {},
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        if document and document.rendered_sections:
            rendered_sections_path.write_text(
                json.dumps(document.rendered_sections, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
        if document and document.content_docx:
            docx_path.write_bytes(document.content_docx)
        return {
            "artifact_dir": str(package_dir),
            "context": str(context_path),
            "context_quality": str(quality_path),
            "generation_meta": str(meta_path),
            "rendered_sections": str(rendered_sections_path) if rendered_sections_path.exists() else "",
            "docx": str(docx_path) if docx_path.exists() else "",
        }

    @staticmethod
    def _incident_items_or_statement(incident_history: dict[str, Any]) -> list[dict[str, Any]]:
        has_incidents = str(incident_history.get("has_incidents", "")).lower()
        items = incident_history.get("items") or []
        if items:
            return items
        if has_incidents in {"false", "нет", "no", "0"}:
            return [
                {
                    "type": "statement",
                    "description": (
                        "За период эксплуатации опасного производственного объекта "
                        "аварии и инциденты, связанные с нарушением требований "
                        "промышленной безопасности, не зарегистрированы."
                    ),
                }
            ]
        if has_incidents in {"true", "да", "yes", "1"}:
            return [
                {
                    "type": "requires_manual_details",
                    "description": "Сведения об авариях/инцидентах требуют заполнения пользователем.",
                }
            ]
        return []

    @staticmethod
    def _normalize_scenarios(selected: list[Any], custom: list[Any]) -> list[dict[str, Any]]:
        scenarios: list[dict[str, Any]] = []
        for item in selected:
            if isinstance(item, dict):
                scenarios.append(item)
            else:
                scenarios.append({"title": str(item), "source": "selected"})
        for item in custom:
            if isinstance(item, dict):
                scenario = dict(item)
                scenario.setdefault("source", "custom")
                scenarios.append(scenario)
            else:
                scenarios.append({"title": str(item), "source": "custom"})
        return scenarios

    @staticmethod
    def _normalize_resources(items: list[Any]) -> list[dict[str, Any]]:
        normalized = []
        for item in items:
            if isinstance(item, dict):
                normalized.append(
                    {
                        "name": item.get("name") or item.get("title") or "—",
                        "type": item.get("type") or item.get("category") or "средство",
                        "quantity": item.get("quantity") or item.get("count") or 1,
                        "location": item.get("location") or item.get("storage_place") or "—",
                        "purpose": item.get("purpose") or "Используется при локализации и ликвидации аварии",
                    }
                )
            else:
                normalized.append(
                    {
                        "name": str(item),
                        "type": "средство",
                        "quantity": 1,
                        "location": "—",
                        "purpose": "Используется при локализации и ликвидации аварии",
                    }
                )
        return normalized

    @staticmethod
    def _join_order(financial: dict[str, Any]) -> str:
        number = financial.get("order_number") or ""
        date = financial.get("order_date") or ""
        if number and date:
            return f"{number} от {date}"
        return number or date or "—"
