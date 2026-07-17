from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


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
    # --- Новые поля карточки организации ---
    org_type: str | None = None
    full_name: str | None = None
    short_name: str | None = None
    legal_address: str | None = None
    actual_address: str | None = None
    postal_address: str | None = None
    phone_additional: str | None = None
    phone_mobile: str | None = None
    fax: str | None = None
    website: str | None = None
    kpp: str | None = None
    ogrnip: str | None = None
    okpo: str | None = None
    # Руководитель
    director_full_name: str | None = None
    director_position: str | None = None
    director_phone: str | None = None
    director_email: str | None = None
    # ИП
    ip_last_name: str | None = None
    ip_first_name: str | None = None
    ip_middle_name: str | None = None
    # Связи
    bank_accounts: list = field(default_factory=list)
    okved_codes: list = field(default_factory=list)
    licenses: list = field(default_factory=list)
    # Служебные
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
