"""Геокодирование через Яндекс Геокодер API."""
import httpx

from src.core.settings import settings
from src.infrastructure.geocoding.types import GeoResult


class YandexGeocoder:
    """Геокодирование адресов через Яндекс API."""

    BASE_URL = "https://geocode-maps.yandex.ru/1.x/"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.yandex_geocoder_api_key

    async def geocode(self, address: str) -> GeoResult | None:
        """
        Геокодирование адреса.
        Возвращает GeoResult или None при ошибке.
        """
        if not self.api_key:
            return None

        params = {
            "apikey": self.api_key,
            "geocode": address,
            "format": "json",
            "results": 1,
            "lang": "ru_RU",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            feature = (
                data.get("response", {})
                .get("GeoObjectCollection", {})
                .get("featureMember", [{}])[0]
                .get("GeoObject", {})
            )

            if not feature:
                return None

            point = feature.get("Point", {})
            meta = feature.get("metaDataProperty", {}).get("GeocoderMetaData", {})

            coords = point.get("pos", "").split()
            if len(coords) < 2:
                return None

            address_data = meta.get("Address", {})
            components = address_data.get("Components", [])

            region = None
            city = None
            for comp in components:
                if comp.get("kind") == "region":
                    region = comp.get("name")
                elif comp.get("kind") == "locality":
                    city = comp.get("name")

            return GeoResult(
                lat=float(coords[1]),
                lon=float(coords[0]),
                full_address=address,
                country="Россия",
                region=region,
                city=city,
                formatted_address=feature.get("name", address),
            )

        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            return None

    async def reverse_geocode(self, lat: float, lon: float) -> GeoResult | None:
        """Обратное геокодирование (координаты → адрес)."""
        if not self.api_key:
            return None

        params = {
            "apikey": self.api_key,
            "geocode": f"{lon},{lat}",
            "format": "json",
            "results": 1,
            "lang": "ru_RU",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            feature = (
                data.get("response", {})
                .get("GeoObjectCollection", {})
                .get("featureMember", [{}])[0]
                .get("GeoObject", {})
            )

            if not feature:
                return None

            return GeoResult(
                lat=lat,
                lon=lon,
                full_address=feature.get("name", ""),
                country="Россия",
                formatted_address=feature.get("name", ""),
            )

        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            return None
