"""Подбор ближайших аварийных служб."""
import json
from pathlib import Path

from src.infrastructure.references.types import EmergencyService

DATA_FILE = Path(__file__).parent / "data" / "services.json"


class EmergencyServiceFinder:
    """Подбор ближайших аварийных служб по расстоянию."""

    def __init__(self):
        self._services: list[EmergencyService] = []
        self._load_data()

    def _load_data(self):
        if DATA_FILE.exists():
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            self._services = [
                EmergencyService(**item) for item in data
            ]

    async def find_nearest(
        self,
        lat: float,
        lon: float,
        service_type: str,
        limit: int = 3,
    ) -> list[EmergencyService]:
        """
        Поиск ближайших служб указанного типа.
        Возвращает отсортированный по расстоянию список.
        """
        filtered = [
            s for s in self._services
            if s.service_type == service_type and s.lat and s.lon
        ]

        # Расчёт расстояния (формула Гаверсинуса)
        for service in filtered:
            service.distance_km = self._haversine(
                lat, lon, service.lat, service.lon
            )

        filtered.sort(key=lambda s: s.distance_km or float("inf"))
        return filtered[:limit]

    async def find_all_nearest(
        self,
        lat: float,
        lon: float,
        limit_per_type: int = 2,
    ) -> dict[str, list[EmergencyService]]:
        """Поиск ближайших служб всех типов."""
        service_types = ["пожарные", "ПАСФ", "скорая", "газовая"]
        result = {}
        for stype in service_types:
            result[stype] = await self.find_nearest(lat, lon, stype, limit_per_type)
        return result

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Расстояние между двумя точками в км (формула Гаверсинуса)."""
        import math

        R = 6371  # Радиус Земли в км
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))
        return R * c
