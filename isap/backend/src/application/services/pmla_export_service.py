"""Export/download application service for PMLA documents."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.infrastructure.repositories.document_repo import DocumentRepository


@dataclass(frozen=True)
class BinaryFileResult:
    """Binary file ready to be streamed by an API handler."""

    filename: str
    content: bytes
    media_type: str


class PmlaExportService:
    """Provides DOCX/PDF download payloads for approved PMLA documents."""

    def __init__(self, document_repo: DocumentRepository) -> None:
        self.document_repo = document_repo

    async def get_docx(self, document_id: UUID) -> BinaryFileResult:
        doc = await self._get_downloadable_document(document_id)
        return BinaryFileResult(
            filename=f"pmla_{document_id}.docx",
            content=doc.content_docx,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    async def get_pdf(self, document_id: UUID) -> BinaryFileResult:
        doc = await self._get_downloadable_document(document_id)
        try:
            from src.infrastructure.pdf.converter import docx_bytes_to_pdf

            pdf_bytes = docx_bytes_to_pdf(doc.content_docx)
        except Exception as exc:  # noqa: BLE001 - converted to API error by caller
            raise RuntimeError(f"Ошибка конвертации в PDF: {exc}") from exc

        return BinaryFileResult(
            filename=f"pmla_{document_id}.pdf",
            content=pdf_bytes,
            media_type="application/pdf",
        )

    async def _get_downloadable_document(self, document_id: UUID):
        doc = await self.document_repo.get(document_id)
        if doc is None:
            raise ValueError("Документ не найден")
        if doc.status != "approved":
            raise PermissionError(
                f"Документ в статусе '{doc.status}'. Скачивание доступно только после утверждения."
            )
        if not doc.content_docx:
            raise FileNotFoundError("Файл документа не найден")
        return doc
