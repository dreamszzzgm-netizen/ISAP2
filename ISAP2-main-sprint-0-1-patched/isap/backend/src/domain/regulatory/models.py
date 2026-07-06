from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class RegulatoryDocument:
    """Нормативный документ в реестре."""

    title: str
    category: str  # НПА | рекомендация | методика расчёта

    id: UUID = field(default_factory=uuid4)
    status: str = "действует"  # действует | рекомендательный | спорный | заменён
    replacement_id: UUID | None = None
    last_verified_at: datetime | None = None
    verification_source: str | None = None
    notes: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
