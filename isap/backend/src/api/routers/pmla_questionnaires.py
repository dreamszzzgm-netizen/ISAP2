"""PMLA Questionnaire Builder API."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.application.services.pmla_questionnaire_service import PmlaQuestionnaireService

router = APIRouter()


class BlockUpdateRequest(BaseModel):
    data: dict | list | str | int | float | bool | None


class CustomScenarioRequest(BaseModel):
    title: str
    description: str | None = None
    source_equipment: str | None = None
    substance: str | None = None
    consequences: str | None = None
    personnel_actions: str | None = None


@router.post("/facility/{facility_id}")
async def create_questionnaire_for_facility(facility_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await PmlaQuestionnaireService(db).create_for_facility(facility_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/facility/{facility_id}")
async def get_questionnaire_by_facility(facility_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await PmlaQuestionnaireService(db).get_by_facility(facility_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{questionnaire_id}")
async def get_questionnaire(questionnaire_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await PmlaQuestionnaireService(db).get_by_id(questionnaire_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{questionnaire_id}/blocks/{block_name}")
async def update_questionnaire_block(
    questionnaire_id: UUID,
    block_name: str,
    request: BlockUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await PmlaQuestionnaireService(db).update_block(questionnaire_id, block_name, request.data)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{questionnaire_id}/custom-scenarios")
async def add_custom_scenario(
    questionnaire_id: UUID,
    request: CustomScenarioRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await PmlaQuestionnaireService(db).add_custom_scenario(questionnaire_id, request.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{questionnaire_id}/custom-scenarios/{index}")
async def delete_custom_scenario(
    questionnaire_id: UUID,
    index: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await PmlaQuestionnaireService(db).remove_custom_scenario(questionnaire_id, index)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{questionnaire_id}/context")
async def build_generation_context(questionnaire_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await PmlaQuestionnaireService(db).build_generation_context(questionnaire_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
