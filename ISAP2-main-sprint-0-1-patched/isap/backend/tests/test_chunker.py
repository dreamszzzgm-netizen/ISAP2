"""Тесты структурного чанкера ПМЛА."""
from src.infrastructure.rag.parsers.section_detector import SectionDetector
from src.infrastructure.rag.parsers.chunker import StructuralChunker, ChunkingConfig
from src.infrastructure.rag.parsers.models import DetectedSection, DetectionReport


def _make_section(section_id: str, title: str, start: int, end: int | None = None) -> DetectedSection:
    return DetectedSection(
        section_id=section_id,
        title=title,
        level=1,
        start_para_idx=start,
        end_para_idx=end,
        confidence=0.9,
    )


def test_empty_report():
    """Пустой отчёт → нет чанков."""
    report = DetectionReport(source_path="test.docx", total_paragraphs=0)
    chunker = StructuralChunker()
    chunks = chunker.chunk(report, [], source_path="test.docx")
    assert chunks == []


def test_single_section_fits_one_chunk():
    """Раздел, помещающийся в один чанк → один чанк."""
    paragraphs = [
        ("Заголовок раздела", None, True),
        ("Текст раздела. " * 50, None, False),  # ~350 символов
    ]
    report = DetectionReport(
        source_path="test.docx",
        total_paragraphs=2,
        detected_sections=[_make_section("section_1", "Раздел 1", 0, 2)],
    )
    chunker = StructuralChunker(ChunkingConfig(max_chunk_chars=2000))
    chunks = chunker.chunk(report, paragraphs, source_path="test.docx")

    assert len(chunks) == 1
    assert chunks[0].section_id == "section_1"
    assert chunks[0].chunk_index == 0
    assert chunks[0].total_chunks_in_section == 1
    assert "Заголовок" in chunks[0].content


def test_large_section_splits():
    """Большой раздел разбивается на подчанки."""
    # Создаём большой раздел из нескольких абзацев (каждый ~300 символов)
    paragraphs = [("Заголовок раздела", None, True)]
    for i in range(20):
        paragraphs.append((f"Абзац {i}: " + "текст " * 50, None, False))  # ~300 символов каждый

    report = DetectionReport(
        source_path="test.docx",
        total_paragraphs=len(paragraphs),
        detected_sections=[_make_section("section_2", "Раздел 2", 0, len(paragraphs))],
    )
    chunker = StructuralChunker(ChunkingConfig(max_chunk_chars=1000, min_chunk_chars=50))
    chunks = chunker.chunk(report, paragraphs, source_path="test.docx")

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.content) <= 1200  # допуск на перекрытие
        assert chunk.section_id == "section_2"


def test_multiple_sections_preserve_order():
    """Множество разделов → чанки в порядке появления."""
    paragraphs = [
        ("Раздел 1", None, True),
        ("Текст 1", None, False),
        ("Раздел 2", None, True),
        ("Текст 2", None, False),
        ("Раздел 3", None, True),
        ("Текст 3", None, False),
    ]
    report = DetectionReport(
        source_path="test.docx",
        total_paragraphs=6,
        detected_sections=[
            _make_section("section_1", "Раздел 1", 0, 2),
            _make_section("section_2", "Раздел 2", 2, 4),
            _make_section("section_3", "Раздел 3", 4, 6),
        ],
    )
    chunker = StructuralChunker()
    chunks = chunker.chunk(report, paragraphs, source_path="test.docx")

    assert len(chunks) == 3
    assert [c.section_id for c in chunks] == ["section_1", "section_2", "section_3"]


def test_metadata_propagation():
    """Метаданные передаются в чанки."""
    paragraphs = [("Заголовок", None, True), ("Текст", None, False)]
    report = DetectionReport(
        source_path="test.docx",
        total_paragraphs=2,
        detected_sections=[_make_section("section_1", "Раздел 1", 0, 2)],
    )
    chunker = StructuralChunker()
    chunks = chunker.chunk(
        report, paragraphs,
        source_path="test.docx",
        metadata={"facility_type": "gas", "hazard_class": "III"},
    )

    assert len(chunks) == 1
    assert chunks[0].metadata["facility_type"] == "gas"
    assert chunks[0].metadata["hazard_class"] == "III"
    assert chunks[0].metadata["section_id"] == "section_1"


def test_chunk_id_unique():
    """ID чанков уникальны."""
    paragraphs = [
        ("Раздел 1", None, True), ("Текст 1", None, False),
        ("Раздел 2", None, True), ("Текст 2", None, False),
    ]
    report = DetectionReport(
        source_path="test.docx",
        total_paragraphs=4,
        detected_sections=[
            _make_section("section_1", "Раздел 1", 0, 2),
            _make_section("section_2", "Раздел 2", 2, 4),
        ],
    )
    chunker = StructuralChunker()
    chunks = chunker.chunk(report, paragraphs, source_path="test.docx")

    ids = [c.id for c in chunks]
    assert len(ids) == len(set(ids))


def test_integration_with_detector():
    """Интеграция: детектор → чанкер на синтетических данных."""
    # Имитируем реальный ПМЛА документ с текстом, совпадающим с паттернами
    # Пустая строка после СОДЕРЖАНИЕ — маркер конца оглавления
    paragraphs = [
        ("СОГЛАСОВАНО", None, True),           # 0 - title_page
        ("СОДЕРЖАНИЕ", None, True),             # 1 - toc
        ("", None, False),                      # 2 - пустая строка (конец ТОС)
        ("ВВЕДЕНИЕ", None, True),               # 3 - introduction
        ("1. Характеристика опасного производственного объекта", None, True),  # 4 - section_1
        ("Описание объекта..." * 20, None, False),
        ("Сценарии наиболее вероятных аварий", None, True),  # 6 - section_2
        ("Описание сценариев..." * 20, None, False),
        ("Специальный раздел плана мероприятий", None, True),  # 8 - special_section
        ("Описание спецраздела..." * 20, None, False),
    ]

    detector = SectionDetector()
    report = detector.detect(paragraphs)

    chunker = StructuralChunker()
    chunks = chunker.chunk(report, paragraphs, source_path="test.docx")

    assert len(chunks) >= 3  # как минимум section_1, section_2, special_section
    section_ids = {c.section_id for c in chunks}
    assert "section_1" in section_ids
    assert "section_2" in section_ids
    assert "special_section" in section_ids
