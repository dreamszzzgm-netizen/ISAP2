"""Сервис справочников — единая точка доступа к JSON-данным."""
from .loader import (
    ReferenceLoader,
    get_substance,
    get_substances_by_facility_type,
    get_accidents,
    get_notification_services,
    get_equipment_kit,
    get_positions,
    get_scenario_instructions,
)

__all__ = [
    "ReferenceLoader",
    "get_substance",
    "get_substances_by_facility_type",
    "get_accidents",
    "get_notification_services",
    "get_equipment_kit",
    "get_positions",
    "get_scenario_instructions",
]
