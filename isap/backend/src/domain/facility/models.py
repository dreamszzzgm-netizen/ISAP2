from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class Equipment:
    """Единица оборудования ОПО."""

    name: str
    equipment_type: str

    id: UUID = field(default_factory=uuid4)
    hazardous_facility_id: UUID | None = None
    serial_number: str | None = None
    manufacturer: str | None = None
    manufacture_year: int | None = None
    specifications: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class HazardousSubstance:
    """Опасное вещество на ОПО."""

    name: str

    id: UUID = field(default_factory=uuid4)
    hazardous_facility_id: UUID | None = None
    cas_number: str | None = None
    quantity_kg: float | None = None
    threshold_quantity_kg: float | None = None
    hazard_properties: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ResponsiblePerson:
    """Ответственное лицо."""

    full_name: str
    position: str

    id: UUID = field(default_factory=uuid4)
    organization_id: UUID | None = None
    role: str | None = None   # safety_manager | director | operator
    phone: str | None = None
    email: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class HazardousFacility:
    """Опасный производственный объект (ОПО)."""

    name: str
    organization_id: UUID

    id: UUID = field(default_factory=uuid4)
    reg_number: str | None = None
    hazard_class: int | None = None   # 1..4
    facility_type: str | None = None  # котельная, газопровод и т.д.
    address: str | None = None
    properties: dict = field(default_factory=dict)

    # Связанные сущности (загружаются отдельно)
    equipment: list[Equipment] = field(default_factory=list)
    substances: list[HazardousSubstance] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
