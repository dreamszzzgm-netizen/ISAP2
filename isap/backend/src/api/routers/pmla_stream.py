"""Streaming API для генерации ПМЛА с прогрессом (SSE)."""
import asyncio
import json
import time
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.api.dependencies import get_document_repo, get_regulatory_repo, get_pmla_sample_repo, get_opo_details_repo, get_facility_repo
from src.infrastructure.llm.providers import get_llm_provider
from src.infrastructure.rag.pipeline import Embedder, Retriever, VectorStore
from src.infrastructure.repositories.document_repo import DocumentRepository
from src.infrastructure.repositories.regulatory_repo import RegulatoryRepository
from src.application.services.enhanced_generator import EnhancedDocumentGenerator

router = APIRouter()


async def generate_with_progress(
    facility_id: UUID,
    document_repo: DocumentRepository,
    regulatory_repo: RegulatoryRepository,
    sample_repo=None,
):
    """Генератор SSE-событий с прогрессом."""

    # Инициализация
    yield _sse("progress", {"step": "init", "message": "Инициализация компонентов...", "percent": 0})
    await asyncio.sleep(0.1)

    try:
        llm = get_llm_provider()
        provider_name = type(llm).__name__
    except Exception:
        llm = None
        provider_name = "fallback"

    yield _sse("progress", {"step": "llm", "message": f"LLM: {provider_name}", "percent": 5})
    await asyncio.sleep(0.1)

    try:
        retriever = Retriever(Embedder(), VectorStore())
    except Exception:
        retriever = None

    yield _sse("progress", {"step": "rag", "message": "RAG инициализирован", "percent": 10})
    await asyncio.sleep(0.1)

    generator = EnhancedDocumentGenerator(
        local_llm=llm,
        external_llm=llm,
        retriever=retriever,
        document_repo=document_repo,
        regulatory_repo=regulatory_repo,
        sample_repo=sample_repo,
    )

    # Создание документа
    yield _sse("progress", {"step": "create_doc", "message": "Создание документа...", "percent": 15})
    await asyncio.sleep(0.1)

    from src.infrastructure.database.models import (
        DocumentModel, HazardousFacilityModel, EquipmentModel,
        HazardousSubstanceModel, ResponsiblePersonModel, OrganizationModel,
    )
    from sqlalchemy import select
    from datetime import datetime, UTC

    result = await document_repo.session.execute(
        select(HazardousFacilityModel).where(HazardousFacilityModel.id == facility_id)
    )
    facility = result.scalar_one_or_none()
    if not facility:
        yield _sse("error", {"message": "ОПО не найден"})
        return

    org_id = facility.organization_id

    # Сборка контекста — сначала из сведений ОПО
    yield _sse("progress", {"step": "context", "message": "Сборка контекста из сведений ОПО...", "percent": 20})
    await asyncio.sleep(0.1)

    # Пробуем собрать контекст из формы «Сведения об ОПО»
    context = None
    equipment = []
    substances = []
    persons = []
    try:
        from src.application.services.opo_service import OpoService
        opo_repo = get_opo_details_repo(document_repo.session)
        facility_repo_inst = get_facility_repo(document_repo.session)
        opo_service = OpoService(opo_repo, facility_repo_inst)
        context = await opo_service.build_generation_context(facility_id)
        equipment = context.get("equipment", [])
        substances = context.get("substances", [])
        persons = context.get("responsible_persons", [])
        yield _sse("progress", {"step": "context", "message": "Контекст собран из сведений ОПО", "percent": 22})
    except Exception:
        pass

    # Fallback: собираем из отдельных таблиц
    if context is None:
        yield _sse("progress", {"step": "context", "message": "Сборка контекста из БД (fallback)...", "percent": 22})
        org_result = await document_repo.session.execute(
            select(OrganizationModel).where(OrganizationModel.id == org_id)
        )
        org = org_result.scalar_one_or_none()

        eq_result = await document_repo.session.execute(
            select(EquipmentModel).where(EquipmentModel.hazardous_facility_id == facility_id)
        )
        equipment = list(eq_result.scalars().all())

        sub_result = await document_repo.session.execute(
            select(HazardousSubstanceModel).where(HazardousSubstanceModel.hazardous_facility_id == facility_id)
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

    # Добавляем аварийные службы если есть координаты
    if facility.latitude and facility.longitude:
        try:
            from src.infrastructure.references.emergency_services import EmergencyServiceFinder
            finder = EmergencyServiceFinder()
            emergency = await finder.find_all_nearest(
                float(facility.latitude), float(facility.longitude)
            )
            context["emergency_services"] = {
                stype: [
                    {"name": s.name, "phone": s.phone, "address": s.address, "distance_km": round(s.distance_km, 1) if s.distance_km else None}
                    for s in services
                ]
                for stype, services in emergency.items()
            }

            # Расчёт сил и средств на основе ближайших служб
            forces = []
            for stype, services in emergency.items():
                for s in services:
                    forces.append({
                        "scenario_name": f"Привлечение {stype}",
                        "items": [
                            {"name": s.name, "unit": "подразделение", "quantity": 1, "location": s.address},
                        ],
                    })
            context["forces_calculation"] = forces
        except Exception:
            pass

    # Средства защиты из оборудования объекта
    protective = []
    for e in equipment:
        eq_type = (e.equipment_type or "").lower()
        if any(kw in eq_type for kw in ["сиз", "огнетушитель", "противогаз", "аптечка", "защит"]):
            protective.append({
                "name": e.name,
                "type": e.equipment_type or "СИЗ",
                "quantity": 1,
                "purpose": "Защита персонала",
            })
    if protective:
        context["protective_equipment"] = protective

    yield _sse("progress", {
        "step": "context_ready",
        "message": f"Контекст: {len(equipment)} оборудование, {len(substances)} веществ, {len(persons)} лиц",
        "percent": 25,
        "context": {
            "equipment_count": len(equipment),
            "substances_count": len(substances),
            "persons_count": len(persons),
        }
    })
    await asyncio.sleep(0.1)

    # Создание записи документа
    doc = DocumentModel(
        hazardous_facility_id=facility_id,
        organization_id=org_id,
        document_type="pmla",
        title="План мероприятий по локализации и ликвидации последствий аварий",
        status="processing",
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    document_repo.session.add(doc)
    await document_repo.session.commit()
    await document_repo.session.refresh(doc)

    yield _sse("progress", {
        "step": "doc_created",
        "message": f"Документ создан: {str(doc.id)[:8]}...",
        "percent": 30,
        "document_id": str(doc.id),
    })

    # Симуляция прогресса по секциям (так как генератор работает синхронно)
    sections = [
        "Общие сведения об организации и объекте",
        "Анализ опасностей и причин аварий",
        "Сценарии аварий",
        "Система оповещения",
        "Силы и средства",
        "Порядок действий",
        "Мероприятия по предупреждению",
    ]

    total = len(sections)
    for i, section in enumerate(sections):
        percent = 30 + int((i / total) * 60)
        yield _sse("progress", {
            "step": "section",
            "message": f"Генерация: {section}",
            "percent": percent,
            "section": section,
            "section_number": i + 1,
            "total_sections": total,
        })
        await asyncio.sleep(0.3)

    # Финальная генерация
    yield _sse("progress", {"step": "generate", "message": "Формирование документа...", "percent": 90})
    await asyncio.sleep(0.2)

    try:
        result = await generator.generate(
            document_id=doc.id,
            context=context,
        )
        yield _sse("progress", {
            "step": "complete",
            "message": "Документ успешно сгенерирован",
            "percent": 100,
            "document_id": str(doc.id),
            "status": result.status,
        })
    except Exception as e:
        yield _sse("error", {"message": f"Ошибка генерации: {str(e)}"})


def _sse(event: str, data: dict) -> str:
    """Форматирование SSE-события."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/generate/stream")
async def generate_stream(
    facility_id: UUID,
    document_repo: DocumentRepository = Depends(get_document_repo),
    regulatory_repo: RegulatoryRepository = Depends(get_regulatory_repo),
    sample_repo=Depends(get_pmla_sample_repo),
):
    """Генерация ПМЛА с прогрессом в реальном времени (SSE)."""
    return StreamingResponse(
        generate_with_progress(facility_id, document_repo, regulatory_repo, sample_repo),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
