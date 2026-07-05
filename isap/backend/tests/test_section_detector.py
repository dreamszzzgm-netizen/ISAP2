"""Comprehensive tests for SectionDetector."""
from __future__ import annotations

import pytest

from src.infrastructure.rag.parsers.section_detector import SectionDetector
from src.infrastructure.rag.parsers.models import DetectionReport, DetectedSection


# Helper to build a paragraph tuple: (text, style_name, is_bold)
def _p(text: str, style: str | None = None, bold: bool = False) -> tuple[str, str | None, bool]:
    return (text, style, bold)


# Canonical texts for all required sections that match the actual regex patterns.
# Note: section_13 pattern requires "обеспечения" (genitive), not "обеспечение".
_REQUIRED_TEXTS: dict[str, str] = {
    "section_1": "Характеристика объекта опасности",
    "section_2": "Сценарии наиболее вероятных аварийных ситуаций",
    "section_3": "Характеристика аварийности и травматизма",
    "section_4": "Количество сил и средств локализации",
    "section_5": "Взаимодействие сил и средств",
    "section_6": "Состав и дислокация сил и средств",
    "section_7": "Готовность сил и средств локализации",
    "section_8": "Управления связи и оповещения",
    "section_9": "Взаимный обмен информацией о ЧС",
    "section_10": "Первоочередные действия при получении сигнала",
    "section_11": "Действия производственного персонала",
    "section_12": "Мероприятия по безопасности населения",
    "section_13": "Материально-техническое обеспечение для обеспечения",
    "special_section": "Специальный раздел",
}


def _build_full_paragraphs() -> list[tuple[str, str | None, bool]]:
    """Build a synthetic document with all 29 sections in correct order.

    The TOC region must be terminated by an empty line appearing at an index
    strictly greater than toc_start + 2 (the detector's heuristic).
    """
    paras: list[tuple[str, str | None, bool]] = []

    # Title page markers (must be in first 15 paragraphs)
    paras.append(_p("СОГЛАСОВАНО", None, True))
    paras.append(_p("УТВЕРЖДАЮ", None, True))

    # Correction log (first 30 paragraphs)
    paras.append(_p("ЖУРНАЛ КОРРЕКТИРОВКИ", None, True))

    # TOC block — needs >= 3 entries so the empty line is past toc_start + 2
    paras.append(_p("СОДЕРЖАНИЕ", None, True))          # idx 3 = toc_start
    paras.append(_p("1  Характеристика объекта", None, False))   # idx 4
    paras.append(_p("2  Сценарии аварий", None, False))          # idx 5
    paras.append(_p("3  Характеристика аварийности", None, False))  # idx 6
    paras.append(_p(""))  # idx 7 — empty line ends TOC (7 > 3+2 ✓)

    # Abbreviations
    paras.append(_p("Обозначений и сокращений", None, True))

    # Terms
    paras.append(_p("Термины и определения", None, True))

    # Introduction
    paras.append(_p("ВВЕДЕНИЕ", None, True))

    # 13 main sections
    for sid in [
        "section_1", "section_2", "section_3", "section_4",
        "section_5", "section_6", "section_7", "section_8",
        "section_9", "section_10", "section_11", "section_12",
        "section_13",
    ]:
        paras.append(_p(_REQUIRED_TEXTS[sid], None, True))

    # Special section
    paras.append(_p(_REQUIRED_TEXTS["special_section"], None, True))

    # Appendices
    paras.append(_p("Приложение 1", None, True))
    paras.append(_p("Приложение №2", None, True))
    paras.append(_p("Приложение №3", None, True))
    paras.append(_p("Приложение 4", None, True))
    paras.append(_p("Приложение №5", None, True))

    # Bibliography
    paras.append(_p("СПИСОК ЛИТЕРАТУРЫ", None, True))

    # Familiarization
    paras.append(_p("ЛИСТ ОЗНАКОМЛЕНИЯ", None, True))

    return paras


# ── Test 1 ────────────────────────────────────────────────────────────

def test_empty_document() -> None:
    """Empty paragraphs list → completeness=0.0, is_valid_pmla=False."""
    detector = SectionDetector()
    report = detector.detect([])
    assert report.completeness_score == 0.0
    assert report.is_valid_pmla is False
    assert report.total_paragraphs == 0
    assert len(report.detected_sections) == 0


# ── Test 2 ────────────────────────────────────────────────────────────

def test_full_pmla_structure() -> None:
    """Simulate 29 sections with correct keywords → completeness=1.0, all found."""
    detector = SectionDetector()
    paras = _build_full_paragraphs()
    report = detector.detect(paras)

    assert report.completeness_score == 1.0
    assert report.is_valid_pmla is True
    assert report.total_paragraphs == len(paras)

    # All 14 required sections must be found
    required_ids = {
        "section_1", "section_2", "section_3", "section_4",
        "section_5", "section_6", "section_7", "section_8",
        "section_9", "section_10", "section_11", "section_12",
        "section_13", "special_section",
    }
    found_ids = {s.section_id for s in report.detected_sections}
    assert required_ids.issubset(found_ids), f"Missing: {required_ids - found_ids}"

    # Check specific sections
    assert any(s.section_id == "section_1" for s in report.detected_sections)
    assert any(s.section_id == "special_section" for s in report.detected_sections)
    assert any(s.section_id == "title_page" for s in report.detected_sections)
    assert any(s.section_id == "appendix_1" for s in report.detected_sections)
    assert any(s.section_id == "bibliography" for s in report.detected_sections)


# ── Test 3 ────────────────────────────────────────────────────────────

def test_broken_numbering() -> None:
    """Broken numbering (1.a.i, 1.11, duplicate 2) → all 14 main sections found.

    The detector uses semantic keywords, not numbering, so broken numbers
    should not prevent detection.
    """
    detector = SectionDetector()

    paras = [
        # Title page
        _p("СОГЛАСОВАНО", None, True),
        # Broken numbering: 1.a.i format
        _p("1.a.i Характеристика объекта опасности"),
        # Some filler
        _p("Текст документа для заполнения"),
        # Broken numbering: 1.11
        _p("1.11 Сценарии наиболее вероятных аварийных ситуаций"),
        # Duplicate number "2"
        _p("2 Характеристика аварийности и травматизма"),
        # Another duplicate "2"
        _p("2 Количество сил и средств локализации"),
        # Remaining sections with various numbering
        _p("Взаимодействие сил и средств"),
        _p("Состав и дислокация сил и средств"),
        _p("Готовность сил и средств локализации"),
        _p("Управления связи и оповещения"),
        _p("Взаимный обмен информацией о ЧС"),
        _p("Первоочередные действия при получении сигнала"),
        _p("Действия производственного персонала"),
        _p("Мероприятия по безопасности населения"),
        _p("Материально-техническое обеспечение для обеспечения"),
        _p("Специальный раздел"),
    ]

    report = detector.detect(paras)
    found_ids = {s.section_id for s in report.detected_sections}

    # All 14 main sections should be found despite broken numbering
    required_ids = {
        "section_1", "section_2", "section_3", "section_4",
        "section_5", "section_6", "section_7", "section_8",
        "section_9", "section_10", "section_11", "section_12",
        "section_13", "special_section",
    }
    assert required_ids.issubset(found_ids), f"Missing: {required_ids - found_ids}"

    # Completeness should be 1.0 since all required sections found
    assert report.completeness_score == 1.0

    # Should have warnings about duplicate numbers
    assert any("Дублирующийся номер" in w for w in report.warnings)


# ── Test 4 ────────────────────────────────────────────────────────────

def test_toc_filtering() -> None:
    """Sections in TOC region (paragraphs 10-40) should NOT be detected.

    Only section headings after the TOC should be picked up.
    """
    detector = SectionDetector()

    paras: list[tuple[str, str | None, bool]] = []
    # Build up to 10 paragraphs before TOC
    for i in range(10):
        paras.append(_p(f"Параграф перед содержанием {i}"))

    # TOC block starts at index 10
    paras.append(_p("СОДЕРЖАНИЕ", None, True))  # idx 10 — TOC marker
    paras.append(_p("1  Характеристика объекта", None, False))  # idx 11
    paras.append(_p("2  Сценарии аварий", None, False))  # idx 12
    paras.append(_p("3  Характеристика аварийности", None, False))  # idx 13
    paras.append(_p(""))  # idx 14 — empty line ends TOC (14 > 10+2 ✓)

    # Real section headings after TOC
    paras.append(_p("Характеристика объекта опасности", None, True))  # idx 15
    paras.append(_p("Сценарии наиболее вероятных аварийных ситуаций", None, True))  # idx 16

    report = detector.detect(paras)

    # The TOC entries (indices 11-13) should NOT be detected
    detected_indices = [s.start_para_idx for s in report.detected_sections]
    assert 11 not in detected_indices
    assert 12 not in detected_indices
    assert 13 not in detected_indices

    # The real sections after TOC (indices 15-16) should be detected
    assert 15 in detected_indices
    assert 16 in detected_indices

    # title_page should not be found (no title markers before TOC at position < 15)
    assert not any(s.section_id == "title_page" for s in report.detected_sections)


# ── Test 5 ────────────────────────────────────────────────────────────

def test_deduplication() -> None:
    """Same section keyword appearing twice (TOC + body) → only first occurrence kept."""
    detector = SectionDetector()

    paras = [
        # Title page
        _p("СОГЛАСОВАНО", None, True),
        # TOC region
        _p("СОДЕРЖАНИЕ", None, True),
        _p("1 Характеристика объекта опасности", None, False),  # TOC entry
        _p("2 Сценарии аварий", None, False),
        _p("3 Термины", None, False),
        _p(""),  # End of TOC (idx 5, > 2+2 ✓)
        # Real body section (after TOC)
        _p("Характеристика объекта опасности", None, True),
        # Another real section
        _p("Сценарии наиболее вероятных аварийных ситуаций", None, True),
    ]

    report = detector.detect(paras)

    # section_1 should appear exactly once
    s1_matches = [s for s in report.detected_sections if s.section_id == "section_1"]
    assert len(s1_matches) == 1

    # The TOC entry is at idx 2, real section is at idx 6
    # After dedup and TOC filtering, only the body version should remain
    assert s1_matches[0].start_para_idx == 6


# ── Test 6 ────────────────────────────────────────────────────────────

def test_appendix_patterns() -> None:
    """Test various appendix formats: Приложение 1, №2, №3, Приложение 4, №5."""
    detector = SectionDetector()

    paras = [
        _p("Приложение 1", None, True),
        _p("Описание первого приложения"),
        _p("Приложение №2", None, True),
        _p("Описание второго приложения"),
        _p("Приложение №3", None, True),
        _p("Описание третьего приложения"),
        _p("Приложение 4", None, True),
        _p("Описание четвёртого приложения"),
        _p("Приложение №5", None, True),
        _p("Описание пятого приложения"),
    ]

    report = detector.detect(paras)
    appendix_ids = {s.section_id for s in report.detected_sections if s.section_id.startswith("appendix_")}

    assert appendix_ids == {"appendix_1", "appendix_2", "appendix_3", "appendix_4", "appendix_5"}

    # Verify ordering by start_para_idx
    appendix_sections = [s for s in report.detected_sections if s.section_id.startswith("appendix_")]
    appendix_sections.sort(key=lambda s: s.start_para_idx)
    assert appendix_sections[0].start_para_idx == 0
    assert appendix_sections[1].start_para_idx == 2
    assert appendix_sections[2].start_para_idx == 4
    assert appendix_sections[3].start_para_idx == 6
    assert appendix_sections[4].start_para_idx == 8


# ── Test 7 ────────────────────────────────────────────────────────────

def test_title_page_in_tables() -> None:
    """Title page markers 'СОГЛАСОВАНО' and 'УТВЕРЖДАЮ' as paragraphs → title_page detected."""
    detector = SectionDetector()

    paras = [
        _p("СОГЛАСОВАНО", None, True),
        _p("Директор ООО «Ромашка»", None, False),
        _p("УТВЕРЖДАЮ", None, True),
        _p("Главный инженер", None, False),
        # Some content after title page
        _p("Общие сведения"),
    ]

    report = detector.detect(paras)

    title_sections = [s for s in report.detected_sections if s.section_id == "title_page"]
    assert len(title_sections) == 1
    # Should be detected at paragraph index 0 (СОГЛАСОВАНО appears first)
    assert title_sections[0].start_para_idx == 0

    # title_page is not in _REQUIRED_IDS but is in _WARNING_IF_MISSING
    # Its detection affects is_valid_pmla (must be True for valid)
    assert "title_page" in {s.section_id for s in report.detected_sections}


# ── Test 8 ────────────────────────────────────────────────────────────

def test_section_boundaries() -> None:
    """Verify end_para_idx is set correctly (next section's start)."""
    detector = SectionDetector()

    paras = [
        _p("СОГЛАСОВАНО", None, True),          # idx 0 — title_page
        _p("Характеристика объекта опасности", None, True),  # idx 1 — section_1
        _p("Some text about section 1"),         # idx 2
        _p("More text about section 1"),         # idx 3
        _p("Сценарии наиболее вероятных аварийных ситуаций", None, True),  # idx 4 — section_2
        _p("Some text about section 2"),         # idx 5
        _p("Характеристика аварийности и травматизма", None, True),  # idx 6 — section_3
    ]

    report = detector.detect(paras)

    section_1 = next(s for s in report.detected_sections if s.section_id == "section_1")
    section_2 = next(s for s in report.detected_sections if s.section_id == "section_2")
    section_3 = next(s for s in report.detected_sections if s.section_id == "section_3")

    # section_1 starts at 1, ends at 4 (start of section_2)
    assert section_1.start_para_idx == 1
    assert section_1.end_para_idx == 4

    # section_2 starts at 4, ends at 6 (start of section_3)
    assert section_2.start_para_idx == 4
    assert section_2.end_para_idx == 6

    # section_3 starts at 6, ends at None (last section)
    assert section_3.start_para_idx == 6
    assert section_3.end_para_idx is None


# ── Test 9 ────────────────────────────────────────────────────────────

def test_confidence_scoring() -> None:
    """Bold text gets higher confidence than non-bold."""
    detector = SectionDetector()

    paras_bold = [
        _p("Характеристика объекта опасности", None, True),
    ]
    paras_not_bold = [
        _p("Характеристика объекта опасности", None, False),
    ]

    report_bold = detector.detect(paras_bold)
    report_not_bold = detector.detect(paras_not_bold)

    bold_section = next(
        (s for s in report_bold.detected_sections if s.section_id == "section_1"), None
    )
    not_bold_section = next(
        (s for s in report_not_bold.detected_sections if s.section_id == "section_1"), None
    )

    assert bold_section is not None
    assert not_bold_section is not None
    assert bold_section.confidence > not_bold_section.confidence

    # Confidence scoring factors:
    #   base: 0.7
    #   pattern match in first 50 chars: +0.1
    #   short text (< 80 chars): +0.05
    #   bold: +0.1
    # Bold total: 0.7 + 0.1 + 0.05 + 0.1 = 0.95
    # Non-bold total: 0.7 + 0.1 + 0.05 = 0.85
    assert bold_section.confidence == pytest.approx(0.95, abs=0.01)
    assert not_bold_section.confidence == pytest.approx(0.85, abs=0.01)


# ── Test 10 ───────────────────────────────────────────────────────────

def test_missing_required_sections() -> None:
    """Only 3 of 14 main sections → completeness < 0.8, is_valid_pmla=False."""
    detector = SectionDetector()

    paras = [
        _p("СОГЛАСОВАНО", None, True),  # title_page
        _p("Характеристика объекта опасности", None, True),  # section_1
        _p("Сценарии наиболее вероятных аварийных ситуаций", None, True),  # section_2
        _p("Характеристика аварийности и травматизма", None, True),  # section_3
    ]

    report = detector.detect(paras)

    # 3 out of 14 required = ~0.214
    assert report.completeness_score == pytest.approx(3 / 14, abs=0.01)
    assert report.completeness_score < 0.8
    assert report.is_valid_pmla is False

    # missing_sections should contain the 11 absent required sections
    assert len(report.missing_sections) == 11
    assert "section_1" not in report.missing_sections
    assert "section_4" in report.missing_sections


# ── Test 11 ───────────────────────────────────────────────────────────

def test_special_section_required() -> None:
    """All 13 numbered sections found but no special_section → is_valid_pmla=False.

    is_valid_pmla requires: completeness >= 0.8 AND title_page AND special_section.
    _REQUIRED_IDS has 14 entries (section_1..13 + special_section).
    With only section_1..13 found (13/14 ≈ 0.929), completeness >= 0.8 holds,
    but special_section is missing → is_valid_pmla must be False.
    """
    detector = SectionDetector()

    paras = [
        _p("СОГЛАСОВАНО", None, True),  # title_page
        # All 13 numbered sections — using texts that match actual regex patterns
        _p("Характеристика объекта опасности", None, True),
        _p("Сценарии наиболее вероятных аварийных ситуаций", None, True),
        _p("Характеристика аварийности и травматизма", None, True),
        _p("Количество сил и средств локализации", None, True),
        _p("Взаимодействие сил и средств", None, True),
        _p("Состав и дислокация сил и средств", None, True),
        _p("Готовность сил и средств локализации", None, True),
        _p("Управления связи и оповещения", None, True),
        _p("Взаимный обмен информацией о ЧС", None, True),
        _p("Первоочередные действия при получении сигнала", None, True),
        _p("Действия производственного персонала", None, True),
        _p("Мероприятия по безопасности населения", None, True),
        _p("Материально-техническое обеспечение для обеспечения", None, True),
        # NO special_section!
    ]

    report = detector.detect(paras)

    # Completeness = 13/14 ≈ 0.929 (>= 0.8)
    assert report.completeness_score == pytest.approx(13 / 14, abs=0.01)
    assert report.completeness_score >= 0.8

    # title_page is found
    assert any(s.section_id == "title_page" for s in report.detected_sections)

    # special_section is NOT found
    assert not any(s.section_id == "special_section" for s in report.detected_sections)

    # Therefore is_valid_pmla must be False
    assert report.is_valid_pmla is False

    # special_section should be in missing_sections
    assert "special_section" in report.missing_sections
