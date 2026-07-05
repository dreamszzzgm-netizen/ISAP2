from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class Document:
    """Документ ПМЛА."""

    hazardous_facility_id: UUID
    organization_id: UUID
    document_type: str

    id: UUID = field(default_factory=uuid4)
    title: str | None = None
    status: str = "draft"
    content_docx: bytes | None = None
    generation_meta: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DocumentVersion:
    """Версия документа."""

    document_id: UUID
    version_number: int
    input_data: dict

    id: UUID = field(default_factory=uuid4)
    prompt_version: str | None = None
    template_version: str | None = None
    calculation_results: dict = field(default_factory=dict)
    reviewer_id: UUID | None = None
    reviewer_decision: str | None = None
    reviewer_comments: list = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CalculationResult:
    """Результат расчёта."""

    document_id: UUID
    method_id: str
    input_params: dict
    results: dict

    id: UUID = field(default_factory=uuid4)
    validation_status: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
