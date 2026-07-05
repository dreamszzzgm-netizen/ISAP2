from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class Organization:
    """Доменная модель организации."""

    name: str
    inn: str

    id: UUID = field(default_factory=uuid4)
    ogrn: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
