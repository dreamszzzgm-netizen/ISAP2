"""Загрузчик справочников из JSON с кэшированием и удобным API."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Путь к справочникам: backend/data/references/
REFERENCES_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "references"


class ReferenceLoader:
    """Загружает JSON-справочники с кэшированием в памяти."""

    _cache: dict[str, dict] = {}

    @classmethod
    def load(cls, name: str) -> dict:
        """Загружает справочник по имени (без расширения .json)."""
        if name in cls._cache:
            return cls._cache[name]

        file_path = REFERENCES_DIR / f"{name}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Справочник не найден: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        cls._cache[name] = data
        logger.info(f"Загружен справочник '{name}' из {file_path}")
        return data

    @classmethod
    def reload(cls, name: str | None = None) -> None:
        """Перезагружает справочник (или все)."""
        if name:
            cls._cache.pop(name, None)
            cls.load(name)
        else:
            cls._cache.clear()

    @classmethod
    def list_available(cls) -> list[str]:
        """Список доступных справочников."""
        if not REFERENCES_DIR.exists():
            return []
        return [p.stem for p in REFERENCES_DIR.glob("*.json")]


# ---------------------------------------------------------------------------
# API для конкретных справочников
# ---------------------------------------------------------------------------

def get_substance(name: str) -> dict | None:
    """
    Получить данные о веществе по названию (с учётом синонимов).

    >>> get_substance("Метан")
    {'name': 'Метан', 'cas_number': '74-82-8', ...}
    >>> get_substance("Природный газ")  # синоним
    {'name': 'Метан', ...}
    """
    data = ReferenceLoader.load("substances")
    name_lower = name.lower().strip()

    for substance in data.get("substances", []):
        if substance["name"].lower() == name_lower:
            return substance
        for synonym in substance.get("synonyms", []):
            if synonym.lower() == name_lower:
                return substance
    return None


def get_substances_by_facility_type(facility_type: str) -> list[dict]:
    """Получить вещества, характерные для данного типа ОПО."""
    data = ReferenceLoader.load("substances")
    return [
        s for s in data.get("substances", [])
        if facility_type in s.get("facility_types", [])
    ]


def get_accidents(
    facility_type: str | None = None,
    years: tuple[int, int] | None = None,
    limit: int | None = None,
) -> list[dict]:
    """
    Получить аварии с фильтрацией.

    Args:
        facility_type: фильтр по типу ОПО (например, "Сеть газопотребления")
        years: диапазон лет (start, end) включительно
        limit: максимальное количество записей
    """
    data = ReferenceLoader.load("accidents")
    accidents = list(data.get("accidents", []))

    if facility_type:
        accidents = [a for a in accidents if a.get("facility_type") == facility_type]

    if years:
        start, end = years
        filtered = []
        for a in accidents:
            try:
                year = int(a["date"].split(".")[-1])
                if start <= year <= end:
                    filtered.append(a)
            except (ValueError, KeyError, IndexError):
                continue
        accidents = filtered

    if limit:
        accidents = accidents[:limit]

    return accidents


def get_notification_services(facility_type: str) -> dict:
    """
    Получить шаблон служб оповещения для типа ОПО.

    Возвращает dict с ключами 'internal' и 'external'.
    Если тип не найден — возвращает шаблон по умолчанию (Сеть газопотребления).
    """
    data = ReferenceLoader.load("notification_services")
    templates = data.get("templates", {})
    return templates.get(facility_type, templates.get("default", {}))


def get_equipment_kit(facility_type: str) -> dict:
    """
    Получить типовое оснащение для типа ОПО.

    Возвращает dict с ключами 'ppe', 'tools', 'equipment'.
    """
    data = ReferenceLoader.load("equipment_kits")
    kits = data.get("kits", {})
    return kits.get(facility_type, kits.get("default", {}))


def get_positions(role: str | None = None) -> list[dict] | dict | None:
    """
    Получить типовые должности.

    Если role=None — возвращает все должности.
    Если role указан — возвращает должность по роли.
    """
    data = ReferenceLoader.load("positions")
    positions = data.get("positions", [])

    if role is None:
        return positions

    for pos in positions:
        if pos.get("role", "").lower() == role.lower():
            return pos
    return None


def get_scenario_instructions(
    facility_type: str,
    scenario_code: str | None = None,
) -> list[dict] | dict | None:
    """
    Получить детальные инструкции по сценариям для типа ОПО.

    Если scenario_code=None — возвращает все сценарии.
    Если scenario_code указан — возвращает конкретный сценарий.
    """
    data = ReferenceLoader.load("scenario_instructions")
    templates = data.get("templates", {})
    scenarios = templates.get(facility_type, [])

    if scenario_code is None:
        return scenarios

    for s in scenarios:
        if s.get("code") == scenario_code:
            return s
    return None
