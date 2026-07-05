"""Общие типы для сервисов генерации."""
from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class Issue:
    """Проблема, обнаруженная при валидации."""

    section: str
    reason: str
    severity: str  # error | warning
    requires_regulatory_review: bool = False


@dataclass
class ValidationResult:
    """Результат валидации документа."""

    passed: bool
    issues: list[Issue] = field(default_factory=list)


@dataclass
class GeneratedDocument:
    """Результат генерации документа."""

    document_id: UUID
    docx_bytes: bytes
    version_number: int
    status: str  # draft | auto_validation_failed | pending_review


@dataclass
class ReviewDecision:
    """Решение ревьюера."""

    document_id: UUID
    reviewer_id: UUID
    decision: str  # approved | rejected
    comments: list[Issue] = field(default_factory=list)


@dataclass
class AIReviewItem:
    """Результат проверки одного пункта чек-листа."""
    check_id: int
    check_name: str
    passed: bool
    confidence: float  # 0.0 - 1.0
    details: str = ""


@dataclass
class AIReviewResult:
    """Результат AI-ревью документа."""
    overall_confidence: float
    decision: str  # auto_approve | escalate_to_human | needs_revision
    items: list[AIReviewItem] = field(default_factory=list)
    summary: str = ""
