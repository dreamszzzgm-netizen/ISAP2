"""Модели данных для детектора разделов ПМЛА."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DetectedSection:
    """Найденный раздел документа."""
    section_id: str                      # "section_2", "special_section"
    title: str                           # каноническое название
    level: int                           # 1, 2, 3
    start_para_idx: int                  # индекс первого параграфа
    end_para_idx: int | None             # индекс первого параграфа СЛЕДУЮЩЕГО раздела
    confidence: float                    # 0.0 - 1.0
    match_pattern: str | None = None     # какой regex сработал (для отладки)


@dataclass
class DetectionReport:
    """Результат разметки документа."""
    source_path: str
    total_paragraphs: int
    detected_sections: list[DetectedSection] = field(default_factory=list)
    missing_sections: list[str] = field(default_factory=list)  # обязательные, которых нет
    completeness_score: float = 0.0      # 0.0 - 1.0
    is_valid_pmla: bool = False          # True если >= 80% + title + special
    warnings: list[str] = field(default_factory=list)  # предупреждения о странностях
