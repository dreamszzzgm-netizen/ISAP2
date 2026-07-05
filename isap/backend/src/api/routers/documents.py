"""Роутер документов — генерация ПМЛА."""
import io
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.infrastructure.llm.providers import get_llm_provider
from src.infrastructure.rag.pipeline import Embedder, VectorStore, Retriever
from src.application.services.document_generator import DocumentGenerator

logger = logging.getLogger(__name__)
router = APIRouter()


class GenerateDocumentRequest(BaseModel):
    facility_id: UUID
    document_type: str = "pmla"
    context: dict


@router.post("/generate")
async def generate_document(request: GenerateDocumentRequest):
    """
    Генерирует документ и возвращает DOCX для скачивания.
    Если LLM не настроен — секции content_type=llm заполняются заглушкой.
    """
    try:
        try:
            llm = get_llm_provider()
        except Exception as e:
            logger.warning("LLM not available, using stub mode: %s", e)
            llm = None

        embedder = Embedder()
        vector_store = VectorStore()
        retriever = Retriever(embedder, vector_store)
        generator = DocumentGenerator(llm=llm, retriever=retriever)

        docx_bytes = await generator.generate(
            document_type=request.document_type,
            context=request.context,
        )

        filename = f"{request.document_type}_{request.facility_id}.docx"
        return StreamingResponse(
            io.BytesIO(docx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Document generation failed")
        raise HTTPException(status_code=500, detail=f"Ошибка генерации: {str(e)}")
