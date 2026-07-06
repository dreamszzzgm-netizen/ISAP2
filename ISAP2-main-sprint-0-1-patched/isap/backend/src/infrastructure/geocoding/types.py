from dataclasses import dataclass


@dataclass
class GeoResult:
    """Результат геокодирования."""

    lat: float
    lon: float
    full_address: str
    country: str = "Россия"
    region: str | None = None
    city: str | None = None
    formatted_address: str | None = None
