"""Роутер реестра нормативных документов."""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from src.api.dependencies import get_regulatory_repo
from src.infrastructure.repositories.regulatory_repo import RegulatoryRepository

router = APIRouter()


class RegulatoryDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    category: str
    status: str
    replacement_id: UUID | None
    last_verified_at: datetime | None
    verification_source: str | None
    notes: str | None


class RegulatoryDocumentCreate(BaseModel):
    title: str
    category: str
    status: str = "действует"
    replacement_id: UUID | None = None
    notes: str | None = None


class RegulatoryDocumentUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    status: str | None = None
    replacement_id: UUID | None = None
    notes: str | None = None


class VerifyRequest(BaseModel):
    status: str
    verification_source: str
    notes: str | None = None


@router.get("/", response_model=list[RegulatoryDocumentResponse])
async def list_regulatory_documents(
    category: str | None = None,
    status: str | None = None,
    repo: RegulatoryRepository = Depends(get_regulatory_repo),
):
    filters = {}
    if category:
        filters["category"] = category
    if status:
        filters["status"] = status
    docs = await repo.get_multi(filters=filters)
    return docs


@router.get("/{document_id}", response_model=RegulatoryDocumentResponse)
async def get_regulatory_document(
    document_id: UUID,
    repo: RegulatoryRepository = Depends(get_regulatory_repo),
):
    doc = await repo.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Нормативный документ не найден")
    return doc


@router.post("/", response_model=RegulatoryDocumentResponse, status_code=201)
async def create_regulatory_document(
    data: RegulatoryDocumentCreate,
    repo: RegulatoryRepository = Depends(get_regulatory_repo),
):
    doc = await repo.create(data.model_dump())
    return doc


@router.delete("/{document_id}", status_code=204)
async def delete_regulatory_document(
    document_id: UUID,
    repo: RegulatoryRepository = Depends(get_regulatory_repo),
):
    deleted = await repo.delete(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Документ не найден")


@router.put("/{document_id}", response_model=RegulatoryDocumentResponse)
async def update_regulatory_document(
    document_id: UUID,
    data: RegulatoryDocumentUpdate,
    repo: RegulatoryRepository = Depends(get_regulatory_repo),
):
    update_data = data.model_dump(exclude_unset=True)
    doc = await repo.update(document_id, update_data)
    if doc is None:
        raise HTTPException(status_code=404, detail="Нормативный документ не найден")
    return doc


@router.post("/{document_id}/verify", response_model=RegulatoryDocumentResponse)
async def verify_regulatory_document(
    document_id: UUID,
    data: VerifyRequest,
    repo: RegulatoryRepository = Depends(get_regulatory_repo),
):
    doc = await repo.verify_status(
        document_id=document_id,
        new_status=data.status,
        verification_source=data.verification_source,
        notes=data.notes,
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Нормативный документ не найден")
    return doc


@router.get("/active/list", response_model=list[RegulatoryDocumentResponse])
async def list_active_documents(
    repo: RegulatoryRepository = Depends(get_regulatory_repo),
):
    return await repo.get_active_documents()


@router.get("/disputed/list", response_model=list[RegulatoryDocumentResponse])
async def list_disputed_documents(
    repo: RegulatoryRepository = Depends(get_regulatory_repo),
):
    return await repo.get_disputed_documents()


@router.get("/replaced/list", response_model=list[RegulatoryDocumentResponse])
async def list_replaced_documents(
    repo: RegulatoryRepository = Depends(get_regulatory_repo),
):
    return await repo.get_replaced_documents()
