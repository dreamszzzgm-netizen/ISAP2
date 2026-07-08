"""Сервис ревью документов."""
from datetime import UTC, datetime
from uuid import UUID

from src.application.services.types import Issue
from src.infrastructure.repositories.document_repo import DocumentRepository

MAX_REGENERATION_ATTEMPTS = 3


class ReviewService:
    """Workflow ревью документов."""

    def __init__(self, document_repo: DocumentRepository):
        self.document_repo = document_repo

    async def submit_for_review(self, document_id: UUID) -> None:
        """Отправка документа на ревью."""
        doc = await self.document_repo.get(document_id)
        if doc is None:
            raise ValueError(f"Документ {document_id} не найден")
        if doc.status not in ("draft", "auto_validation_failed"):
            raise ValueError(
                f"Документ в статусе '{doc.status}', "
                "можно отправить на ревью только из статуса draft или auto_validation_failed"
            )
        await self.document_repo.update(document_id, {
            "status": "pending_review",
            "submitted_at": datetime.now(UTC).replace(tzinfo=None),
        })

    async def approve(
        self,
        document_id: UUID,
        reviewer_id: UUID | str,
        comments: list | str | None = None,
    ) -> None:
        """Утверждение документа."""
        doc = await self.document_repo.get(document_id)
        if doc is None:
            raise ValueError(f"Документ {document_id} не найден")
        if doc.status != "pending_review":
            raise ValueError(
                f"Документ в статусе '{doc.status}', "
                "можно утвердить только из статуса pending_review"
            )

        now = datetime.now(UTC).replace(tzinfo=None)
        target_year = now.year + 5
        try:
            review_date = datetime(target_year, now.month, now.day)
        except ValueError:
            review_date = datetime(target_year, now.month, 28)
        await self.document_repo.update(
            document_id,
            {
                "status": "approved",
                "approved_at": now,
                "review_date": review_date,
                "regeneration_count": 0,
                "updated_at": now,
            },
        )

        await self._save_version(
            document_id=document_id,
            reviewer_id=reviewer_id,
            decision="approved",
            comments=comments,
        )

    async def reject(
        self,
        document_id: UUID,
        reviewer_id: UUID | str,
        issues: list[Issue],
    ) -> dict:
        """Возврат документа на доработку.

        Возвращает:
            {"action": "regenerated"|"manual_required", "sections": [...]}
        """
        doc = await self.document_repo.get(document_id)
        if doc is None:
            raise ValueError(f"Документ {document_id} не найден")
        if doc.status != "pending_review":
            raise ValueError(
                f"Документ в статусе '{doc.status}', "
                "можно вернуть только из статуса pending_review"
            )

        # Извлекаем уникальные имена разделов из замечаний
        rejected_sections = list({i.section for i in issues if i.section})

        # Проверяем количество попыток перегенерации
        regen_count = (doc.regeneration_count or 0) + 1

        if regen_count >= MAX_REGENERATION_ATTEMPTS:
            # Превышен лимит — ручная доработка
            await self.document_repo.update(
                document_id,
                {
                    "status": "manual_intervention_required",
                    "rejected_at": datetime.now(UTC).replace(tzinfo=None),
                    "regeneration_count": regen_count,
                    "updated_at": datetime.now(UTC).replace(tzinfo=None),
                },
            )
            action = "manual_required"
        else:
            # Автоматическая перегенерация отклонённых разделов
            await self.document_repo.update(
                document_id,
                {
                    "status": "rejected",
                    "rejected_at": datetime.now(UTC).replace(tzinfo=None),
                    "regeneration_count": regen_count,
                    "updated_at": datetime.now(UTC).replace(tzinfo=None),
                },
            )
            action = "regenerated"

        # Запись версии с замечаниями
        comments_data = [
            {"section": i.section, "reason": i.reason, "severity": i.severity}
            for i in issues
        ]
        await self._save_version(
            document_id=document_id,
            reviewer_id=reviewer_id,
            decision="rejected",
            comments=comments_data,
        )

        return {"action": action, "sections": rejected_sections, "regeneration_count": regen_count}

    async def get_status(self, document_id: UUID) -> dict:
        """Получение статуса документа."""
        doc = await self.document_repo.get(document_id)
        if doc is None:
            raise ValueError(f"Документ {document_id} не найден")

        version = await self.document_repo.get_latest_version(document_id)
        issues = []
        if version and version.reviewer_comments:
            issues = version.reviewer_comments

        return {
            "document_id": str(doc.id),
            "status": doc.status,
            "issues": issues,
            "version_number": version.version_number if version else None,
            "regeneration_count": doc.regeneration_count or 0,
        }

    async def _save_version(
        self,
        document_id: UUID,
        reviewer_id: UUID,
        decision: str,
        comments: str | list | None,
    ) -> None:
        """Сохранение версии документа с решением ревьюера."""
        from src.application.services.regulatory_snapshot import (
            collect_regulatory_snapshot,
        )
        from src.infrastructure.database.models import DocumentVersionModel

        latest = await self.document_repo.get_latest_version(document_id)
        next_version = (latest.version_number + 1) if latest else 1

        input_data = {}
        if latest and latest.input_data:
            input_data = latest.input_data

        regulatory_snapshot = await collect_regulatory_snapshot(
            getattr(self.document_repo, "session", None)
        )

        version = DocumentVersionModel(
            document_id=document_id,
            version_number=next_version,
            input_data=input_data,
            reviewer_id=reviewer_id if isinstance(reviewer_id, UUID) else None,
            reviewer_decision=decision,
            reviewer_comments=comments if isinstance(comments, list) else [{"comment": comments}],
            regulatory_snapshot=regulatory_snapshot,
        )
        await self.document_repo.add_version(version)
