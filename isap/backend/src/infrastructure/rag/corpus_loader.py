"""Загрузка корпуса знаний в ChromaDB: нормативы + готовые ПМЛА."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

from src.infrastructure.database.engine import async_session_factory
from src.infrastructure.database.models import DocumentModel, RegulatoryDocumentModel
from src.infrastructure.rag.pipeline import (
    Chunker,
    DocumentLoader,
    Embedder,
    VectorStore,
)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
SAMPLE_DIR = BASE_DIR / "data" / "corpus"
PMLA_CONTENT = BASE_DIR.parent / "pmla_content.txt"


@dataclass
class LoadResult:
    regulatory_loaded: int = 0
    pmla_loaded: int = 0
    files_loaded: int = 0
    total_chunks: int = 0
    errors: list[str] | None = None


class CorpusLoader:
    """Загружает корпус знаний в ChromaDB."""

    def __init__(self):
        self._loader = DocumentLoader()
        self._chunker = Chunker()
        self._embedder = Embedder()
        self._store = VectorStore()

    async def load_all(self) -> LoadResult:
        """Полная загрузка: нормативы из БД + файлы из data/corpus/ + pmla_content.txt."""
        result = LoadResult(errors=[])

        # 1. Нормативные документы из БД
        try:
            count = await self._load_regulatory_docs()
            result.regulatory_loaded = count
        except Exception as e:
            logger.error("Ошибка загрузки нормативов: %s", e)
            result.errors.append(f"regulatory: {e}")

        # 2. Готовые ПМЛА из БД
        try:
            count = await self._load_pmla_documents()
            result.pmla_loaded = count
        except Exception as e:
            logger.error("Ошибка загрузки ПМЛА из БД: %s", e)
            result.errors.append(f"pmla_db: {e}")

        # 3. Файлы из data/corpus/
        try:
            count = await self._load_files(SAMPLE_DIR)
            result.files_loaded = count
        except Exception as e:
            logger.error("Ошибка загрузки файлов: %s", e)
            result.errors.append(f"files: {e}")

        # 4. pmla_content.txt (эталонный ПМЛА)
        if PMLA_CONTENT.exists():
            try:
                docs = self._loader.load(PMLA_CONTENT)
                chunks = self._chunker.chunk(docs)
                if chunks:
                    embedded = await self._embedder.embed_chunks(chunks)
                    self._store.add(embedded)
                    result.files_loaded += 1
                    result.total_chunks += len(embedded)
                    logger.info("Загружен pmla_content.txt: %d чанков", len(embedded))
            except Exception as e:
                logger.error("Ошибка загрузки pmla_content.txt: %s", e)
                result.errors.append(f"pmla_content: {e}")

        if not result.errors:
            result.errors = None

        logger.info(
            "Корпус загружен: нормативов=%d, ПМЛА_БД=%d, файлов=%d, чанков=%d",
            result.regulatory_loaded, result.pmla_loaded, result.files_loaded, result.total_chunks,
        )
        return result

    async def _load_regulatory_docs(self) -> int:
        """Загрузка нормативных документов из БД как текстовых чанков."""
        async with async_session_factory() as session:
            result = await session.execute(select(RegulatoryDocumentModel))
            docs = list(result.scalars().all())

        if not docs:
            logger.info("Нет нормативных документов в БД")
            return 0

        from src.infrastructure.rag.pipeline import Document as RagDoc

        documents = []
        for doc in docs:
            text_parts = [f"Нормативный документ: {doc.title}"]
            if doc.category:
                text_parts.append(f"Категория: {doc.category}")
            if doc.status:
                text_parts.append(f"Статус: {doc.status}")
            if doc.notes:
                text_parts.append(f"Описание: {doc.notes}")
            content = "\n".join(text_parts)
            documents.append(RagDoc(
                content=content,
                source=f"regulatory:{doc.id}",
                metadata={"type": "regulatory", "category": doc.category, "status": doc.status},
            ))

        chunks = self._chunker.chunk(documents)
        if chunks:
            embedded = await self._embedder.embed_chunks(chunks)
            self._store.add(embedded)
            logger.info("Загружено %d нормативов → %d чанков", len(docs), len(embedded))

        return len(docs)

    async def _load_pmla_documents(self) -> int:
        """Загрузка утверждённых ПМЛА из БД."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(DocumentModel).where(DocumentModel.status == "approved")
            )
            docs = list(result.scalars().all())

        if not docs:
            logger.info("Нет утверждённых ПМЛА в БД")
            return 0

        from src.infrastructure.rag.pipeline import Document as RagDoc

        documents = []
        for doc in docs:
            meta = doc.generation_meta or {}
            content_parts = [f"ПМЛА документ: {doc.title or 'Без названия'}"]
            if meta.get("sections"):
                for section in meta["sections"]:
                    if isinstance(section, dict) and section.get("content"):
                        content_parts.append(section["content"])
            content = "\n".join(content_parts)
            if len(content) > 50:
                documents.append(RagDoc(
                    content=content,
                    source=f"pmla:{doc.id}",
                    metadata={"type": "pmla", "document_type": doc.document_type},
                ))

        chunks = self._chunker.chunk(documents)
        if chunks:
            embedded = await self._embedder.embed_chunks(chunks)
            self._store.add(embedded)
            logger.info("Загружено %d ПМЛА → %d чанков", len(docs), len(embedded))

        return len(docs)

    async def _load_files(self, directory: Path) -> int:
        """Загрузка файлов из директории."""
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            logger.info("Создана директория: %s", directory)
            return 0


        count = 0
        for ext in ("*.txt", "*.pdf", "*.docx"):
            for path in directory.glob(ext):
                try:
                    docs = self._loader.load(path)
                    chunks = self._chunker.chunk(docs)
                    if chunks:
                        embedded = await self._embedder.embed_chunks(chunks)
                        self._store.add(embedded)
                        count += 1
                        logger.info("Загружен %s: %d чанков", path.name, len(embedded))
                except Exception as e:
                    logger.warning("Ошибка загрузки %s: %s", path, e)

        return count
