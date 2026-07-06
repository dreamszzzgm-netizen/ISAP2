"""Структурная модель блоков для генерации ПМЛА.

Блоки — формат обмена между движками и _build_docx().
Заменяют плоский текст на семантически значимые структуры:
заголовки, абзацы, таблицы, изображения.

Сериализация: блоки → JSON-совместимые dict (для JSONB в БД).
Десериализация: JSON → блоки (при загрузке из БД).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class HeadingBlock:
    """Заголовок раздела или подраздела."""
    text: str
    level: int = 1          # 0 = заголовок документа, 1 = раздел, 2 = подраздел
    center: bool = False


@dataclass
class ParagraphBlock:
    """Абзац текста."""
    text: str
    bold: bool = False


@dataclass
class TableBlock:
    """Таблица с заголовками и строками данных."""
    headers: list[str]
    rows: list[list[str]]
    caption: str | None = None   # например "Таблица 14. Схема оповещения"


@dataclass
class ImageBlock:
    """Изображение (пока заглушка — источник данных отдельным тикетом)."""
    path: str
    width_cm: float = 16.5       # макс. ширина печатной обл. A4 при полях 3+1.5см
    caption: str | None = None


Block = HeadingBlock | ParagraphBlock | TableBlock | ImageBlock

# ── Сериализация ──────────────────────────────────────────────────────────

_BLOCK_TYPES = {
    "heading": HeadingBlock,
    "paragraph": ParagraphBlock,
    "table": TableBlock,
    "image": ImageBlock,
}


def serialize_blocks(blocks: list[Block]) -> list[dict[str, Any]]:
    """Конвертирует list[Block] → JSON-совместимый list[dict]."""
    result = []
    for b in blocks:
        if isinstance(b, HeadingBlock):
            result.append({"__type__": "heading", "text": b.text, "level": b.level, "center": b.center})
        elif isinstance(b, ParagraphBlock):
            result.append({"__type__": "paragraph", "text": b.text, "bold": b.bold})
        elif isinstance(b, TableBlock):
            result.append({"__type__": "table", "headers": b.headers, "rows": b.rows, "caption": b.caption})
        elif isinstance(b, ImageBlock):
            result.append({"__type__": "image", "path": b.path, "width_cm": b.width_cm, "caption": b.caption})
    return result


def deserialize_blocks(data: list[dict[str, Any]]) -> list[Block]:
    """Конвертирует JSON-совместимый list[dict] → list[Block]."""
    result = []
    for item in data:
        block_type = item.get("__type__")
        cls = _BLOCK_TYPES.get(block_type)
        if cls is None:
            continue
        kwargs = {k: v for k, v in item.items() if k != "__type__"}
        result.append(cls(**kwargs))
    return result
