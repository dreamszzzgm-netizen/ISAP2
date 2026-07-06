"""Парсеры документов ПМЛА для авто-разметки разделов."""
from src.infrastructure.rag.parsers.chunker import (
    ChunkingConfig,
    StructuralChunk,
    StructuralChunker,
)
from src.infrastructure.rag.parsers.models import DetectedSection, DetectionReport
from src.infrastructure.rag.parsers.section_detector import SectionDetector

__all__ = [
    "DetectedSection", "DetectionReport", "SectionDetector",
    "StructuralChunker", "StructuralChunk", "ChunkingConfig",
]
