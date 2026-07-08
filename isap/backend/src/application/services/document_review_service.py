"""Сервис ручной проверки документов ПМЛА.

Workflow ручной проверки: инженер проверяет документ, ставит статус,
добавляет замечания и переводит в "Готов к выдаче".
"""
from datetime import UTC, datetime
from uuid import UUID

from src.infrastructure.repositories.document_repo import DocumentRepository

# Допустимые переходы статусов ручной проверки
REVIEW_STATUS_LABELS = {
    "draft": "Черновик",
    "generated": "Сгенерирован",
    "needs_review": "Требует проверки",
    "in_review": "На проверке",
    "needs_changes": "Требует исправления",
    "approved": "Проверен инженером",
    "ready_to_issue": "Готов к выдаче",
    "issued": "Выдан клиенту",
    "archived": "Архив",
}

# Разрешённые переходы: {from_status: [list of allowed to_status]}
ALLOWED_TRANSITIONS = {
    "draft": ["needs_review"],
    "generated": ["needs_review", "in_review"],
    "needs_review": ["in_review"],
    "in_review": ["needs_changes", "approved"],
    "needs_changes": ["in_review"],
    "approved": ["ready_to_issue"],
    "ready_to_issue": ["issued"],
    "issued": ["archived"],
    "archived": [],
}


class DocumentReviewService:
    """Сервис ручной проверки документов."""

    def __init__(self, document_repo: DocumentRepository):
        self.document_repo = document_repo

    async def get_review_status(self, document_id: UUID) -> dict:
        """Получение статуса ручной проверки документа."""
        doc = await self.document_repo.get(document_id)
        if doc is None:
            raise ValueError(f"Документ {document_id} не найден")

        review_status = doc.review_status or "needs_review"

        def _format_datetime(dt):
            if dt is None:
                return None
            if isinstance(dt, str):
                return dt
            return dt.isoformat()

        return {
            "document_id": str(doc.id),
            "review_status": review_status,
            "review_status_label": REVIEW_STATUS_LABELS.get(review_status, review_status),
            "review_comment": doc.review_comment,
            "reviewed_by": doc.reviewed_by,
            "reviewed_at": _format_datetime(doc.reviewed_at),
            "issued_at": _format_datetime(doc.issued_at),
            "allowed_transitions": ALLOWED_TRANSITIONS.get(review_status, []),
        }

    async def update_review_status(
        self,
        document_id: UUID,
        review_status: str,
        review_comment: str | None = None,
        reviewed_by: str | None = None,
    ) -> dict:
        """Обновление статуса ручной проверки документа."""
        doc = await self.document_repo.get(document_id)
        if doc is None:
            raise ValueError(f"Документ {document_id} не найден")

        current_status = doc.review_status or "needs_review"

        # Проверка допустимости перехода
        allowed = ALLOWED_TRANSITIONS.get(current_status, [])
        if review_status not in allowed:
            raise ValueError(
                f"Недопустимый переход: '{current_status}' → '{review_status}'. "
                f"Допустимые переходы: {allowed}"
            )

        now = datetime.now(UTC).replace(tzinfo=None)
        update_data: dict = {
            "review_status": review_status,
            "updated_at": now,
        }

        if review_comment is not None:
            update_data["review_comment"] = review_comment
        if reviewed_by is not None:
            update_data["reviewed_by"] = reviewed_by

        # Временные метки
        if review_status in ("in_review", "approved"):
            update_data["reviewed_at"] = now
        if review_status == "issued":
            update_data["issued_at"] = now

        await self.document_repo.update(document_id, update_data)

        return await self.get_review_status(document_id)

    async def set_initial_review_status(self, document_id: UUID, quality_status: str = "ok") -> None:
        """Установка начального статуса проверки после генерации.

        quality_status: "ok" | "warning" | "critical"
        """
        if quality_status == "critical":
            review_status = "needs_changes"
        else:
            review_status = "needs_review"

        await self.document_repo.update(document_id, {
            "review_status": review_status,
        })
