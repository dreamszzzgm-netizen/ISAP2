"""Структурный чанкер ПМЛА — разбивает документ на чанки по разделам.

Использует DetectionReport от SectionDetector для определения границ разделов.
Каждый раздел становится чанком (или разбивается на подчанки, если слишком большой).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from src.infrastructure.rag.parsers.models import DetectedSection, DetectionReport


@dataclass
class StructuralChunk:
    """Структурный чанк документа ПМЛА."""
    content: str
    source: str
    section_id: str
    section_title: str
    chunk_index: int  # индекс чанка внутри раздела
    total_chunks_in_section: int  # всего чанков в этом разделе
    start_para_idx: int
    end_para_idx: int | None
    metadata: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        """Уникальный ID чанка."""
        key = f"{self.source}:{self.section_id}:{self.chunk_index}"
        return hashlib.md5(key.encode()).hexdigest()


@dataclass
class ChunkingConfig:
    """Конфигурация чанкинга."""
    max_chunk_chars: int = 2000  # максимальный размер чанка в символах
    overlap_chars: int = 200  # перекрытие между подчанками
    min_chunk_chars: int = 100  # минимальный размер чанка


class StructuralChunker:
    """Разбивает документ ПМЛА на структурные чанки по границам разделов.

    Использует DetectionReport от SectionDetector для определения
    границ каждого раздела. Каждый раздел становится отдельным чанком.
    Если раздел слишком большой, он разбивается на подчанки с перекрытием.

    Пример использования::

        detector = SectionDetector()
        report = detector.detect(paragraphs)

        chunker = StructuralChunker()
        chunks = chunker.chunk(report, paragraphs, source_path="file.docx")
    """

    def __init__(self, config: ChunkingConfig | None = None):
        self._config = config or ChunkingConfig()

    def chunk(
        self,
        report: DetectionReport,
        paragraphs: list[tuple[str, str | None, bool]],
        source_path: str = "",
        metadata: dict | None = None,
    ) -> list[StructuralChunk]:
        """Разбивает документ на структурные чанки.

        Args:
            report: Отчёт детектора разделов.
            paragraphs: Список параграфов (text, style, is_bold).
            source_path: Путь к исходному файлу.
            metadata: Дополнительные метаданные для каждого чанка.

        Returns:
            Список структурных чанков.
        """
        if not report.detected_sections:
            return []

        base_metadata = metadata or {}
        chunks: list[StructuralChunk] = []

        # Сортируем разделы по порядку появления
        sorted_sections = sorted(
            report.detected_sections,
            key=lambda s: s.start_para_idx,
        )

        for section in sorted_sections:
            section_chunks = self._chunk_section(
                section=section,
                paragraphs=paragraphs,
                source_path=source_path,
                base_metadata=base_metadata,
            )
            chunks.extend(section_chunks)

        return chunks

    def _chunk_section(
        self,
        section: DetectedSection,
        paragraphs: list[tuple[str, str | None, bool]],
        source_path: str,
        base_metadata: dict,
    ) -> list[StructuralChunk]:
        """Разбивает один раздел на чанки."""
        # Определяем границы раздела
        start = section.start_para_idx
        end = section.end_para_idx if section.end_para_idx is not None else len(paragraphs)

        # Извлекаем текст раздела
        section_text_parts = []
        for i in range(start, end):
            if i < len(paragraphs):
                text = paragraphs[i][0]
                if text and text.strip():
                    section_text_parts.append(text.strip())

        if not section_text_parts:
            return []

        section_text = "\n".join(section_text_parts)

        # Если раздел помещается в один чанк
        if len(section_text) <= self._config.max_chunk_chars:
            return [self._make_chunk(
                content=section_text,
                source=source_path,
                section=section,
                chunk_index=0,
                total_chunks=1,
                metadata=base_metadata,
            )]

        # Разбиваем большой раздел на подчанки
        return self._split_large_section(
            section_text=section_text,
            source_path=source_path,
            section=section,
            base_metadata=base_metadata,
        )

    def _split_large_section(
        self,
        section_text: str,
        source_path: str,
        section: DetectedSection,
        base_metadata: dict,
    ) -> list[StructuralChunk]:
        """Разбивает большой раздел на подчанки с перекрытием."""
        chunks = []
        chunk_index = 0

        # Разбиваем по абзацам (переносы строк)
        paragraphs = section_text.split("\n")
        current_chunk_parts = []
        current_chunk_len = 0

        for para in paragraphs:
            para_len = len(para)

            # Если добавление абзаца превысит лимит
            if current_chunk_len + para_len > self._config.max_chunk_chars:
                # Сохраняем текущий чанк
                if current_chunk_parts:
                    chunk_text = "\n".join(current_chunk_parts)
                    if len(chunk_text) >= self._config.min_chunk_chars:
                        chunks.append(self._make_chunk(
                            content=chunk_text,
                            source=source_path,
                            section=section,
                            chunk_index=chunk_index,
                            total_chunks=0,  # заполним позже
                            metadata=base_metadata,
                        ))
                        chunk_index += 1

                # Начинаем новый чанк с перекрытием
                overlap_parts = self._get_overlap(current_chunk_parts)
                current_chunk_parts = overlap_parts + [para]
                current_chunk_len = sum(len(p) for p in current_chunk_parts)
            else:
                current_chunk_parts.append(para)
                current_chunk_len += para_len

        # Последний чанк
        if current_chunk_parts:
            chunk_text = "\n".join(current_chunk_parts)
            if len(chunk_text) >= self._config.min_chunk_chars:
                chunks.append(self._make_chunk(
                    content=chunk_text,
                    source=source_path,
                    section=section,
                    chunk_index=chunk_index,
                    total_chunks=0,
                    metadata=base_metadata,
                ))

        # Обновляем total_chunks
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks_in_section = total

        return chunks

    def _get_overlap(self, parts: list[str]) -> list[str]:
        """Возвращает последние части для перекрытия."""
        if not parts:
            return []

        overlap_parts = []
        overlap_len = 0

        for part in reversed(parts):
            if overlap_len + len(part) > self._config.overlap_chars:
                break
            overlap_parts.insert(0, part)
            overlap_len += len(part)

        return overlap_parts

    def _make_chunk(
        self,
        content: str,
        source: str,
        section: DetectedSection,
        chunk_index: int,
        total_chunks: int,
        metadata: dict,
    ) -> StructuralChunk:
        """Создаёт чанк с метаданными."""
        chunk_metadata = {
            **metadata,
            "section_id": section.section_id,
            "section_title": section.title,
            "section_level": section.level,
            "confidence": section.confidence,
        }

        return StructuralChunk(
            content=content,
            source=source,
            section_id=section.section_id,
            section_title=section.title,
            chunk_index=chunk_index,
            total_chunks_in_section=total_chunks,
            start_para_idx=section.start_para_idx,
            end_para_idx=section.end_para_idx,
            metadata=chunk_metadata,
        )
