from dataclasses import dataclass


@dataclass
class EmergencyService:
    """Аварийная служба."""

    name: str
    service_type: str  # пожарные | ПАСФ | скорая | газовая
    phone: str
    address: str | None = None
    lat: float | None = None
    lon: float | None = None
    distance_km: float | None = None


@dataclass
class EquipmentItem:
    """Элемент перечня СИЗ/оборудования."""

    name: str
    category: str  # СИЗ | инструмент | материал
    quantity: int = 1
    unit: str = "шт"
    notes: str | None = None


@dataclass
class EquipmentList:
    """Перечень оборудования по типу ОПО и классу опасности."""

    facility_type: str
    hazard_class: int
    items: list[EquipmentItem]
