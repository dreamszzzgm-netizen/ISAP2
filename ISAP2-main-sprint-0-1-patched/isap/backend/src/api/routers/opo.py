"""Роутер для формы «Сведения об ОПО»."""
from uuid import UUID
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from src.api.dependencies import get_opo_details_repo, get_facility_repo
from src.infrastructure.repositories.opo_details_repo import OpoDetailsRepository
from src.infrastructure.repositories.facility_repo import FacilityRepository
from src.application.services.opo_service import OpoService

router = APIRouter()


class OpoDetailsRequest(BaseModel):
    form_data: dict


def _get_service(
    opo_repo: OpoDetailsRepository = Depends(get_opo_details_repo),
    facility_repo: FacilityRepository = Depends(get_facility_repo),
) -> OpoService:
    return OpoService(opo_repo, facility_repo)


@router.get("/{facility_id}/details")
async def get_details(
    facility_id: UUID,
    service: OpoService = Depends(_get_service),
):
    return await service.get_details(facility_id)


@router.post("/{facility_id}/details")
async def save_details(
    facility_id: UUID,
    request: OpoDetailsRequest,
    service: OpoService = Depends(_get_service),
):
    return await service.save_details(facility_id, request.form_data)


@router.get("/{facility_id}/export/docx")
async def export_docx(
    facility_id: UUID,
    service: OpoService = Depends(_get_service),
):
    details = await service.get_details(facility_id)
    from src.infrastructure.export.brand_engine import generate_opo_docx
    docx_bytes = generate_opo_docx(details)
    fname = quote(f"Сведения_об_ОПО_{str(facility_id)[:8]}.docx")
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{fname}"},
    )


@router.get("/{facility_id}/export/pdf")
async def export_pdf(
    facility_id: UUID,
    service: OpoService = Depends(_get_service),
):
    details = await service.get_details(facility_id)
    from src.infrastructure.export.brand_engine import generate_opo_pdf
    pdf_bytes = generate_opo_pdf(details)
    fname = quote(f"Сведения_об_ОПО_{str(facility_id)[:8]}.pdf")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{fname}"},
    )
