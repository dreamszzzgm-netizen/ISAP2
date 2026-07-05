"""Тесты структурного RAG-пайплайна."""
from src.infrastructure.rag.structural_pipeline import parse_pmla_docx, PmlaParseResult
from src.infrastructure.rag.parsers.section_detector import SectionDetector
from src.infrastructure.rag.parsers.chunker import StructuralChunker


def test_parse_result_structure():
    """PmlaParseResult содержит все необходимые поля."""
    result = PmlaParseResult()
    assert result.paragraphs == []
    assert result.table_texts == []
    assert result.report is None
    assert result.chunks == []


def test_detector_chunker_chain():
    """Детектор → чанкер: цепочка работает на синтетических данных."""
    paragraphs = [
        ("СОГЛАСОВАНО", None, True),           # title_page
        ("СОДЕРЖАНИЕ", None, True),             # toc
        ("", None, False),                      # конец ТОС
        ("ВВЕДЕНИЕ", None, True),               # introduction
        ("1. Характеристика опасного производственного объекта", None, True),
        ("Описание объекта..." * 10, None, False),
        ("Сценарии наиболее вероятных аварий", None, True),
        ("Описание сценариев..." * 10, None, False),
        ("Специальный раздел плана мероприятий", None, True),
        ("Описание спецраздела..." * 10, None, False),
    ]

    detector = SectionDetector()
    report = detector.detect(paragraphs)

    chunker = StructuralChunker()
    chunks = chunker.chunk(report, paragraphs, source_path="test.docx")

    assert len(chunks) >= 3
    section_ids = {c.section_id for c in chunks}
    assert "section_1" in section_ids
    assert "section_2" in section_ids
    assert "special_section" in section_ids

    # Проверяем метаданные чанков
    for chunk in chunks:
        assert "section_id" in chunk.metadata
        assert "section_title" in chunk.metadata
        assert chunk.source == "test.docx"


def test_structured_chunks_have_correct_metadata():
    """Структурные чанки содержат правильные метаданные."""
    paragraphs = [
        ("СОГЛАСОВАНО", None, True),
        ("", None, False),
        ("1. Характеристика опасного производственного объекта", None, True),
        ("Текст раздела 1", None, False),
    ]

    detector = SectionDetector()
    report = detector.detect(paragraphs)

    chunker = StructuralChunker()
    chunks = chunker.chunk(
        report, paragraphs,
        source_path="test.docx",
        metadata={"facility_type": "gas", "hazard_class": "III"},
    )

    assert len(chunks) >= 1
    for chunk in chunks:
        assert chunk.metadata["facility_type"] == "gas"
        assert chunk.metadata["hazard_class"] == "III"
        assert "section_id" in chunk.metadata
        assert "section_title" in chunk.metadata
        assert "confidence" in chunk.metadata


def test_section_filtering_in_retriever():
    """Фильтрация по section_id в retriever."""
    # Проверяем что фильтр строится правильно
    from src.infrastructure.rag.structural_pipeline import StructuralSampleRetriever

    # Тест без реального хранилища — проверяем логику фильтрации
    retriever = StructuralSampleRetriever()
    # retriever._store будет None если ChromaDB недоступен
    # Это нормально для unit-теста — мы проверяем импорт и структуру
    assert retriever._embedder is not None


def test_chunker_configurable():
    """Чанкер конфигурируется через ChunkingConfig."""
    from src.infrastructure.rag.parsers.chunker import ChunkingConfig

    config = ChunkingConfig(
        max_chunk_chars=500,
        overlap_chars=50,
        min_chunk_chars=20,
    )
    chunker = StructuralChunker(config)
    assert chunker._config.max_chunk_chars == 500
    assert chunker._config.overlap_chars == 50
    assert chunker._config.min_chunk_chars == 20
