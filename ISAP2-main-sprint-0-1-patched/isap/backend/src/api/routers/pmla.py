"""Роутер ПМЛА — генерация, статус, ревью, скачивание."""
import io
import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.api.dependencies import (
    get_document_repo,
    get_regulatory_repo,
    get_scenario_matrix_repo,
    get_pmla_sample_repo,
    get_opo_details_repo,
    get_facility_repo,
)
from src.application.services.calculations import CalculationRegistry  # noqa: F401 — регистрация методик
from src.application.services.enhanced_generator import EnhancedDocumentGenerator
from src.application.services.review_service import ReviewService
from src.application.services.types import Issue
from src.infrastructure.llm.providers import get_llm_provider
from src.infrastructure.rag.pipeline import Embedder, Retriever, VectorStore
from src.infrastructure.repositories.document_repo import DocumentRepository
from src.infrastructure.repositories.regulatory_repo import RegulatoryRepository
from src.infrastructure.repositories.scenario_matrix_repo import ScenarioMatrixRepository

logger = logging.getLogger(__name__)
router = APIRouter()

# Импорт модулей расчёта для регистрации методик
from src.application.services.calculations import explosion_zone  # noqa: F401
from src.application.services.calculations import thermal_radiation  # noqa: F401
from src.application.services.calculations import toxic_exposure  # noqa: F401


class GeneratePMLARequest(BaseModel):
    facility_id: UUID
    context: dict | None = None  # Опционально: если не передан, собирается из БД
    regenerate_sections: list[str] | None = None


class ReviewRequest(BaseModel):
    reviewer_id: str | UUID = "anonymous"
    decision: str  # approved | rejected
    comments: list[dict] | None = None


def _equipment_value(item, key: str, default=None):
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)





@router.post("/generate")
async def generate_pmla(
    request: GeneratePMLARequest,
    document_repo: DocumentRepository = Depends(get_document_repo),
    regulatory_repo: RegulatoryRepository = Depends(get_regulatory_repo),
    scenario_matrix_repo: ScenarioMatrixRepository = Depends(get_scenario_matrix_repo),
    sample_repo=Depends(get_pmla_sample_repo),
    opo_repo=Depends(get_opo_details_repo),
    facility_repo_dep=Depends(get_facility_repo),
):
    """
    Генерация ПМЛА.
    Возвращает document_id и статус processing.

    Если context не передан — автоматически собирается из сведений ОПО (opo_details).
    """
    try:
        # Создаём запись документа
        from src.infrastructure.database.models import (
            DocumentModel, HazardousFacilityModel, EquipmentModel,
            HazardousSubstanceModel, ResponsiblePersonModel, OrganizationModel,
        )
        from sqlalchemy import select

        # Получаем facility из БД
        result = await document_repo.session.execute(
            select(HazardousFacilityModel).where(
                HazardousFacilityModel.id == request.facility_id
            )
        )
        facility = result.scalar_one_or_none()
        if facility is None:
            raise HTTPException(status_code=404, detail="Объект ОПО не найден")

        org_id = facility.organization_id

        # Если контекст не передан — собираем из сведений ОПО
        if request.context is None:
            from src.application.services.opo_service import OpoService
            opo_service = OpoService(opo_repo, facility_repo_dep)

            # Пробуем собрать контекст из формы «Сведения об ОПО»
            try:
                request.context = await opo_service.build_generation_context(request.facility_id)
                logger.info(f"Контекст собран из сведений ОПО для facility {request.facility_id}")
            except Exception as e:
                logger.warning(f"Не удалось собрать контекст из ОПО: {e}, используется fallback из БД")
                # Fallback: собираем из отдельных таблиц
                org_result = await document_repo.session.execute(
                    select(OrganizationModel).where(OrganizationModel.id == org_id)
                )
                org = org_result.scalar_one_or_none()

                eq_result = await document_repo.session.execute(
                    select(EquipmentModel).where(
                        EquipmentModel.hazardous_facility_id == request.facility_id
                    )
                )
                equipment = list(eq_result.scalars().all())

                sub_result = await document_repo.session.execute(
                    select(HazardousSubstanceModel).where(
                        HazardousSubstanceModel.hazardous_facility_id == request.facility_id
                    )
                )
                substances = list(sub_result.scalars().all())

                persons_result = await document_repo.session.execute(
                    select(ResponsiblePersonModel).where(
                        ResponsiblePersonModel.organization_id == org_id
                    )
                )
                persons = list(persons_result.scalars().all())

                request.context = {
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
                        "commissioning_date": facility.commissioning_date.isoformat() if facility.commissioning_date else None,
                        "inventory_number": facility.inventory_number,
                    },
                    "equipment": [
                        {"name": e.name, "equipment_type": e.equipment_type, "serial_number": e.serial_number}
                        for e in equipment
                    ],
                    "substances": [
                        {"name": s.name, "quantity_kg": float(s.quantity_kg) if s.quantity_kg else 0,
                         "cas_number": s.cas_number, "hazard_properties": s.hazard_properties or {}}
                        for s in substances
                    ],
                    "responsible_persons": [
                        {"full_name": p.full_name, "position": p.position, "role": p.role, "phone": p.phone}
                        for p in persons
                    ],
                }

            # Добавляем аварийные службы если есть координаты
            lat = request.context.get("facility", {}).get("latitude")
            lng = request.context.get("facility", {}).get("longitude")
            if lat and lng:
                try:
                    from src.infrastructure.references.emergency_services import EmergencyServiceFinder
                    finder = EmergencyServiceFinder()
                    emergency = await finder.find_all_nearest(float(lat), float(lng))
                    request.context["emergency_services"] = {
                        stype: [
                            {"name": s.name, "phone": s.phone, "address": s.address, "distance_km": round(s.distance_km, 1) if s.distance_km else None}
                            for s in services
                        ]
                        for stype, services in emergency.items()
                    }

                    forces = []
                    for stype, services in emergency.items():
                        for s in services:
                            forces.append({
                                "scenario_name": f"Привлечение {stype}",
                                "items": [
                                    {"name": s.name, "unit": "подразделение", "quantity": 1, "location": s.address},
                                ],
                            })
                    request.context["forces_calculation"] = forces
                except Exception:
                    pass

            # Средства защиты из оборудования объекта
            equipment = request.context.get("equipment", [])
            protective = []
            for e in equipment:
                equipment_type = _equipment_value(e, "equipment_type", "")
                eq_type = (equipment_type or "").lower()
                if any(kw in eq_type for kw in ["сиз", "огнетушитель", "противогаз", "аптечка", "защит"]):
                    protective.append({
                        "name": _equipment_value(e, "name", ""),
                        "type": equipment_type or "СИЗ",
                        "quantity": 1,
                        "purpose": "Защита персонала",
                    })
            if protective:
                request.context["protective_equipment"] = protective

        doc = DocumentModel(
            hazardous_facility_id=request.facility_id,
            organization_id=org_id,
            document_type="pmla",
            title="План мероприятий по локализации и ликвидации последствий аварий",
            status="processing",
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        document_repo.session.add(doc)
        await document_repo.session.commit()
        await document_repo.session.refresh(doc)

        # Инициализация компонентов
        try:
            llm = get_llm_provider()
        except Exception as e:
            logger.warning("LLM not available: %s", e)
            llm = None

        try:
            embedder = Embedder()
            vector_store = VectorStore()
            retriever = Retriever(embedder, vector_store)
        except Exception as e:
            logger.warning("RAG/ChromaDB not available: %s", e)
            retriever = None

        generator = EnhancedDocumentGenerator(
            local_llm=llm,
            external_llm=llm,
            retriever=retriever,
            document_repo=document_repo,
            regulatory_repo=regulatory_repo,
            scenario_matrix_repo=scenario_matrix_repo,
            sample_repo=sample_repo,
        )

        result = await generator.generate(
            document_id=doc.id,
            context=request.context,
            regenerate_sections=request.regenerate_sections,
        )

        return {
            "document_id": str(doc.id),
            "status": result.status,
            "version": result.version_number,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("PMLA generation failed")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера при генерации ПМЛА")


@router.get("/{document_id}/status")
async def get_pmla_status(
    document_id: UUID,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Получение статуса документа."""
    try:
        review_service = ReviewService(document_repo)
        status = await review_service.get_status(document_id)
        return status
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{document_id}/review")
async def review_pmla(
    document_id: UUID,
    request: ReviewRequest,
    document_repo: DocumentRepository = Depends(get_document_repo),
    regulatory_repo: RegulatoryRepository = Depends(get_regulatory_repo),
    scenario_matrix_repo: ScenarioMatrixRepository = Depends(get_scenario_matrix_repo),
    sample_repo=Depends(get_pmla_sample_repo),
):
    """Ревью документа (утверждение/возврат).

    При отклонении автоматически перегенерируются отклонённые разделы
    (если не превышен лимит попыток).
    """
    try:
        review_service = ReviewService(document_repo)

        if request.decision == "approved":
            await review_service.approve(
                document_id=document_id,
                reviewer_id=request.reviewer_id,
                comments=request.comments,
            )
            return {"status": "approved"}

        elif request.decision == "rejected":
            issues = [
                Issue(
                    section=c.get("section", ""),
                    reason=c.get("reason", ""),
                    severity=c.get("severity", "error"),
                )
                for c in (request.comments or [])
            ]
            reject_result = await review_service.reject(
                document_id=document_id,
                reviewer_id=request.reviewer_id,
                issues=issues,
            )

            # Автоматическая перегенерация отклонённых разделов
            if reject_result["action"] == "regenerated" and reject_result["sections"]:
                try:
                    await _auto_regenerate_sections(
                        document_id=document_id,
                        sections=reject_result["sections"],
                        document_repo=document_repo,
                        regulatory_repo=regulatory_repo,
                        scenario_matrix_repo=scenario_matrix_repo,
                        sample_repo=sample_repo,
                    )
                except Exception as e:
                    logger.warning("Auto-regeneration failed: %s", e)

            return {
                "status": "rejected",
                "action": reject_result["action"],
                "regenerated_sections": reject_result["sections"],
                "regeneration_count": reject_result["regeneration_count"],
            }

        else:
            raise HTTPException(
                status_code=400,
                detail="decision должен быть 'approved' или 'rejected'",
            )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


async def _auto_regenerate_sections(
    document_id: UUID,
    sections: list[str],
    document_repo: DocumentRepository,
    regulatory_repo: RegulatoryRepository,
    scenario_matrix_repo: ScenarioMatrixRepository,
    sample_repo,
) -> None:
    """Автоматическая перегенерация указанных разделов."""
    from src.infrastructure.database.models import (
        HazardousFacilityModel, EquipmentModel,
        HazardousSubstanceModel, ResponsiblePersonModel, OrganizationModel,
    )
    from sqlalchemy import select

    doc = await document_repo.get(document_id)
    if doc is None or not doc.hazardous_facility_id:
        return

    result = await document_repo.session.execute(
        select(HazardousFacilityModel).where(HazardousFacilityModel.id == doc.hazardous_facility_id)
    )
    facility = result.scalar_one_or_none()
    if facility is None:
        return

    org_id = facility.organization_id
    org_result = await document_repo.session.execute(
        select(OrganizationModel).where(OrganizationModel.id == org_id)
    )
    org = org_result.scalar_one_or_none()

    eq_result = await document_repo.session.execute(
        select(EquipmentModel).where(EquipmentModel.hazardous_facility_id == doc.hazardous_facility_id)
    )
    equipment = list(eq_result.scalars().all())

    sub_result = await document_repo.session.execute(
        select(HazardousSubstanceModel).where(HazardousSubstanceModel.hazardous_facility_id == doc.hazardous_facility_id)
    )
    substances = list(sub_result.scalars().all())

    persons_result = await document_repo.session.execute(
        select(ResponsiblePersonModel).where(ResponsiblePersonModel.organization_id == org_id)
    )
    persons = list(persons_result.scalars().all())

    context = {
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
            "commissioning_date": facility.commissioning_date.isoformat() if facility.commissioning_date else None,
            "inventory_number": facility.inventory_number,
        },
        "equipment": [
            {"name": e.name, "equipment_type": e.equipment_type, "serial_number": e.serial_number}
            for e in equipment
        ],
        "substances": [
            {"name": s.name, "quantity_kg": float(s.quantity_kg) if s.quantity_kg else 0,
             "cas_number": s.cas_number, "hazard_properties": s.hazard_properties or {}}
            for s in substances
        ],
        "responsible_persons": [
            {"full_name": p.full_name, "position": p.position, "role": p.role, "phone": p.phone}
            for p in persons
        ],
    }

    try:
        llm = get_llm_provider()
    except Exception:
        llm = None

    try:
        embedder = Embedder()
        vector_store = VectorStore()
        retriever = Retriever(embedder, vector_store)
    except Exception:
        retriever = None

    generator = EnhancedDocumentGenerator(
        local_llm=llm,
        external_llm=llm,
        retriever=retriever,
        document_repo=document_repo,
        regulatory_repo=regulatory_repo,
        scenario_matrix_repo=scenario_matrix_repo,
        sample_repo=sample_repo,
    )

    await generator.generate(
        document_id=document_id,
        context=context,
        regenerate_sections=sections,
    )


@router.get("/{document_id}/download")
async def download_pmla(
    document_id: UUID,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Скачивание DOCX (только для approved)."""
    doc = await document_repo.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Документ не найден")

    if doc.status != "approved":
        raise HTTPException(
            status_code=403,
            detail=f"Документ в статусе '{doc.status}'. Скачивание доступно только после утверждения.",
        )

    if not doc.content_docx:
        raise HTTPException(status_code=404, detail="Файл документа не найден")

    filename = f"pmla_{document_id}.docx"
    return StreamingResponse(
        io.BytesIO(doc.content_docx),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{document_id}/download/pdf")
async def download_pmla_pdf(
    document_id: UUID,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Скачивание PDF (конвертация из DOCX)."""
    doc = await document_repo.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Документ не найден")

    if doc.status != "approved":
        raise HTTPException(
            status_code=403,
            detail=f"Документ в статусе '{doc.status}'. Скачивание доступно только после утверждения.",
        )

    if not doc.content_docx:
        raise HTTPException(status_code=404, detail="Файл документа не найден")

    try:
        from src.infrastructure.pdf.converter import docx_bytes_to_pdf
        pdf_bytes = docx_bytes_to_pdf(doc.content_docx)
    except Exception as e:
        logger.exception("PDF conversion failed")
        raise HTTPException(status_code=500, detail=f"Ошибка конвертации в PDF: {e}")

    filename = f"pmla_{document_id}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{document_id}/preview")
async def preview_pmla(
    document_id: UUID,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Превью документа ПМЛА — HTML-представление содержимого."""
    doc = await document_repo.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Документ не найден")

    from sqlalchemy import select
    from src.infrastructure.database.models import HazardousFacilityModel, OrganizationModel

    facility_name = ""
    org_name = ""
    if doc.hazardous_facility_id:
        result = await document_repo.session.execute(
            select(HazardousFacilityModel.name, OrganizationModel.name.label("org_name"))
            .outerjoin(OrganizationModel, HazardousFacilityModel.organization_id == OrganizationModel.id)
            .where(HazardousFacilityModel.id == doc.hazardous_facility_id)
        )
        row = result.first()
        if row:
            facility_name = row[0] or ""
            org_name = row[1] or ""

    sections = []
    generation_meta = doc.generation_meta or {}
    calc_results = generation_meta.get("calculation_results", [])

    if doc.content_docx:
        try:
            import docx
            import io as _io
            d = docx.Document(_io.BytesIO(doc.content_docx))
            current_section = None
            for para in d.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                style_name = para.style.name if para.style else ""
                if "Heading" in style_name or (para.runs and para.runs[0].bold and len(text) > 5):
                    if current_section:
                        sections.append(current_section)
                    current_section = {"title": text, "content": []}
                elif current_section is not None:
                    current_section["content"].append(text)
                else:
                    current_section = {"title": "", "content": [text]}
            if current_section:
                sections.append(current_section)
        except Exception:
            pass

    issues = generation_meta.get("validation_issues", [])

    return {
        "document_id": str(doc.id),
        "title": doc.title or "ПМЛА",
        "facility_name": facility_name,
        "organization_name": org_name,
        "status": doc.status,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "sections": sections,
        "calculations": calc_results,
        "issues": issues,
    }


@router.get("/")
async def list_pmla_documents(
    skip: int = 0,
    limit: int = 100,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Список документов ПМЛА."""
    from sqlalchemy import select
    from src.infrastructure.database.models import DocumentModel, HazardousFacilityModel

    query = (
        select(DocumentModel, HazardousFacilityModel.name.label("facility_name"))
        .outerjoin(HazardousFacilityModel, DocumentModel.hazardous_facility_id == HazardousFacilityModel.id)
        .where(DocumentModel.document_type == "pmla")
        .order_by(DocumentModel.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await document_repo.session.execute(query)
    rows = result.all()

    return [
        {
            "id": str(doc.id),
            "title": doc.title,
            "status": doc.status,
            "facility_id": str(doc.hazardous_facility_id) if doc.hazardous_facility_id else None,
            "facility_name": facility_name,
            "organization_id": str(doc.organization_id) if doc.organization_id else None,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc, facility_name in rows
    ]


@router.get("/expiring")
async def list_expiring_documents(
    days: int = 30,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Документы с истекающим сроком пересмотра."""
    from datetime import timedelta
    from sqlalchemy import select, and_
    from src.infrastructure.database.models import DocumentModel, HazardousFacilityModel

    now = datetime.now(UTC).replace(tzinfo=None)
    threshold = now + timedelta(days=days)

    query = (
        select(DocumentModel, HazardousFacilityModel.name.label("facility_name"))
        .outerjoin(HazardousFacilityModel, DocumentModel.hazardous_facility_id == HazardousFacilityModel.id)
        .where(and_(
            DocumentModel.document_type == "pmla",
            DocumentModel.status == "approved",
            DocumentModel.review_date.isnot(None),
            DocumentModel.review_date <= threshold,
            DocumentModel.review_date >= now,
        ))
        .order_by(DocumentModel.review_date.asc())
    )
    result = await document_repo.session.execute(query)
    rows = result.all()

    return [
        {
            "id": str(doc.id),
            "title": doc.title,
            "facility_name": facility_name,
            "status": doc.status,
            "review_date": doc.review_date.isoformat() if doc.review_date else None,
            "days_remaining": (doc.review_date - now).days if doc.review_date else None,
        }
        for doc, facility_name in rows
    ]


@router.get("/overdue")
async def list_overdue_documents(
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Просроченные документы."""
    from sqlalchemy import select, and_
    from src.infrastructure.database.models import DocumentModel, HazardousFacilityModel

    now = datetime.now(UTC).replace(tzinfo=None)

    query = (
        select(DocumentModel, HazardousFacilityModel.name.label("facility_name"))
        .outerjoin(HazardousFacilityModel, DocumentModel.hazardous_facility_id == HazardousFacilityModel.id)
        .where(and_(
            DocumentModel.document_type == "pmla",
            DocumentModel.status == "approved",
            DocumentModel.review_date.isnot(None),
            DocumentModel.review_date < now,
        ))
        .order_by(DocumentModel.review_date.asc())
    )
    result = await document_repo.session.execute(query)
    rows = result.all()

    return [
        {
            "id": str(doc.id),
            "title": doc.title,
            "facility_name": facility_name,
            "status": doc.status,
            "review_date": doc.review_date.isoformat() if doc.review_date else None,
            "days_overdue": (now - doc.review_date).days if doc.review_date else None,
        }
        for doc, facility_name in rows
    ]


class RegenerateRequest(BaseModel):
    sections: list[str]


@router.post("/{document_id}/regenerate")
async def regenerate_sections(
    document_id: UUID,
    request: RegenerateRequest,
    document_repo: DocumentRepository = Depends(get_document_repo),
    regulatory_repo: RegulatoryRepository = Depends(get_regulatory_repo),
    scenario_matrix_repo: ScenarioMatrixRepository = Depends(get_scenario_matrix_repo),
    sample_repo=Depends(get_pmla_sample_repo),
):
    """Частичная перегенерация разделов ПМЛА."""
    doc = await document_repo.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Документ не найден")

    if not doc.hazardous_facility_id:
        raise HTTPException(status_code=400, detail="Документ не привязан к объекту ОПО")

    # Сборка контекста из БД
    from src.infrastructure.database.models import (
        HazardousFacilityModel, EquipmentModel,
        HazardousSubstanceModel, ResponsiblePersonModel, OrganizationModel,
    )
    from sqlalchemy import select

    result = await document_repo.session.execute(
        select(HazardousFacilityModel).where(HazardousFacilityModel.id == doc.hazardous_facility_id)
    )
    facility = result.scalar_one_or_none()
    if facility is None:
        raise HTTPException(status_code=404, detail="ОПО не найден")

    org_id = facility.organization_id

    org_result = await document_repo.session.execute(
        select(OrganizationModel).where(OrganizationModel.id == org_id)
    )
    org = org_result.scalar_one_or_none()

    eq_result = await document_repo.session.execute(
        select(EquipmentModel).where(EquipmentModel.hazardous_facility_id == doc.hazardous_facility_id)
    )
    equipment = list(eq_result.scalars().all())

    sub_result = await document_repo.session.execute(
        select(HazardousSubstanceModel).where(HazardousSubstanceModel.hazardous_facility_id == doc.hazardous_facility_id)
    )
    substances = list(sub_result.scalars().all())

    persons_result = await document_repo.session.execute(
        select(ResponsiblePersonModel).where(ResponsiblePersonModel.organization_id == org_id)
    )
    persons = list(persons_result.scalars().all())

    context = {
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
            "commissioning_date": facility.commissioning_date.isoformat() if facility.commissioning_date else None,
            "inventory_number": facility.inventory_number,
        },
        "equipment": [
            {"name": e.name, "equipment_type": e.equipment_type, "serial_number": e.serial_number}
            for e in equipment
        ],
        "substances": [
            {"name": s.name, "quantity_kg": float(s.quantity_kg) if s.quantity_kg else 0,
             "cas_number": s.cas_number, "hazard_properties": s.hazard_properties or {}}
            for s in substances
        ],
        "responsible_persons": [
            {"full_name": p.full_name, "position": p.position, "role": p.role, "phone": p.phone}
            for p in persons
        ],
    }

    # Инициализация компонентов
    try:
        llm = get_llm_provider()
    except Exception:
        llm = None

    try:
        embedder = Embedder()
        vector_store = VectorStore()
        retriever = Retriever(embedder, vector_store)
    except Exception:
        retriever = None

    generator = EnhancedDocumentGenerator(
        local_llm=llm,
        external_llm=llm,
        retriever=retriever,
        document_repo=document_repo,
        regulatory_repo=regulatory_repo,
        scenario_matrix_repo=scenario_matrix_repo,
        sample_repo=sample_repo,
    )

    result = await generator.generate(
        document_id=document_id,
        context=context,
        regenerate_sections=request.sections,
    )

    return {
        "document_id": str(result.document_id),
        "status": result.status,
        "version": result.version_number,
        "regenerated_sections": request.sections,
    }


@router.post("/{document_id}/restore/{version_id}")
async def restore_version(
    document_id: UUID,
    version_id: UUID,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Восстановление документа из старой версии."""
    from sqlalchemy import select
    from src.infrastructure.database.models import DocumentVersionModel
    from datetime import UTC, datetime

    doc = await document_repo.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Документ не найден")

    result = await document_repo.session.execute(
        select(DocumentVersionModel).where(DocumentVersionModel.id == version_id)
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=404, detail="Версия не найдена")

    if not version.content_docx:
        raise HTTPException(status_code=400, detail="Версия не содержит DOCX")

    # Восстанавливаем содержимое и статус
    await document_repo.update(
        document_id,
        {
            "content_docx": version.content_docx,
            "rendered_sections": version.input_data.get("rendered_sections", {}) if isinstance(version.input_data, dict) else {},
            "status": "pending_review",
            "updated_at": datetime.now(UTC).replace(tzinfo=None),
        },
    )

    return {
        "document_id": str(document_id),
        "restored_from_version": version.version_number,
        "status": "pending_review",
    }


@router.post("/{document_id}/ai-review")
async def run_ai_review(
    document_id: UUID,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Запуск AI-ревью документа (ручной триггер)."""
    from sqlalchemy import select
    from src.infrastructure.database.models import DocumentVersionModel
    from src.application.services.ai_reviewer import AIReviewer

    doc = await document_repo.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Документ не найден")

    if not doc.rendered_sections:
        raise HTTPException(status_code=400, detail="Документ не содержит отрендеренных разделов")

    # Контекст из последней версии
    result = await document_repo.session.execute(
        select(DocumentVersionModel)
        .where(DocumentVersionModel.document_id == document_id)
        .order_by(DocumentVersionModel.version_number.desc())
        .limit(1)
    )
    version = result.scalar_one_or_none()
    context = version.input_data if version and isinstance(version.input_data, dict) else {}

    # Инициализация LLM
    try:
        llm = get_llm_provider()
    except Exception:
        raise HTTPException(status_code=503, detail="LLM недоступен")

    reviewer = AIReviewer(llm)
    ai_result = await reviewer.review(doc.rendered_sections, context)

    # Сохраняем результат в последнюю версию
    if version:
        from sqlalchemy import update
        await document_repo.session.execute(
            update(DocumentVersionModel)
            .where(DocumentVersionModel.id == version.id)
            .values(
                ai_review_confidence=ai_result.overall_confidence,
                ai_review_decision=ai_result.decision,
                ai_review_items=[
                    {"id": i.check_id, "name": i.check_name, "passed": i.passed, "confidence": i.confidence, "details": i.details}
                    for i in ai_result.items
                ],
                ai_review_summary=ai_result.summary,
            )
        )
        await document_repo.session.commit()

    return {
        "document_id": str(document_id),
        "confidence": ai_result.overall_confidence,
        "decision": ai_result.decision,
        "items": [
            {"id": i.check_id, "name": i.check_name, "passed": i.passed, "confidence": i.confidence, "details": i.details}
            for i in ai_result.items
        ],
        "summary": ai_result.summary,
    }


@router.get("/{document_id}/ai-review")
async def get_ai_review(
    document_id: UUID,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Результат AI-ревью документа."""
    from sqlalchemy import select
    from src.infrastructure.database.models import DocumentVersionModel

    doc = await document_repo.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Документ не найден")

    result = await document_repo.session.execute(
        select(DocumentVersionModel)
        .where(DocumentVersionModel.document_id == document_id)
        .order_by(DocumentVersionModel.version_number.desc())
        .limit(1)
    )
    version = result.scalar_one_or_none()

    if version is None or version.ai_review_decision is None:
        raise HTTPException(status_code=404, detail="AI-ревью не проводилось")

    return {
        "document_id": str(document_id),
        "version_number": version.version_number,
        "confidence": float(version.ai_review_confidence) if version.ai_review_confidence else None,
        "decision": version.ai_review_decision,
        "items": version.ai_review_items or [],
        "summary": version.ai_review_summary,
    }


@router.get("/{document_id}/versions")
async def list_document_versions(
    document_id: UUID,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """История версий документа."""
    from sqlalchemy import select
    from src.infrastructure.database.models import DocumentVersionModel

    doc = await document_repo.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Документ не найден")

    result = await document_repo.session.execute(
        select(DocumentVersionModel)
        .where(DocumentVersionModel.document_id == document_id)
        .order_by(DocumentVersionModel.version_number.desc())
    )
    versions = list(result.scalars().all())

    return [
        {
            "id": str(v.id),
            "version_number": v.version_number,
            "reviewer_id": str(v.reviewer_id) if v.reviewer_id else None,
            "reviewer_decision": v.reviewer_decision,
            "reviewer_comments": v.reviewer_comments or [],
            "regulatory_snapshot": v.regulatory_snapshot or [],
            "prompt_version": v.prompt_version,
            "template_version": v.template_version,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


@router.get("/methods/list")
async def list_calculation_methods():
    """Список доступных расчётных методик."""
    return CalculationRegistry.list_methods()
