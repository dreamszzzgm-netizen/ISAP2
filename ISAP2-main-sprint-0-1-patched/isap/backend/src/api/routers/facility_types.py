"""Роутер справочника типов ОПО."""
from fastapi import APIRouter

from src.infrastructure.references.facility_types import get_facility_types

router = APIRouter()


@router.get("/")
async def list_facility_types():
    """Список типов опасных производственных объектов."""
    types = get_facility_types()
    return [
        {
            "code": ft.code,
            "name": ft.name,
            "description": ft.description,
            "hazard_class_default": ft.hazard_class_default,
        }
        for ft in types
    ]
