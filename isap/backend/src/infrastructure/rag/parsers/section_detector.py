"""Детектор разделов ПМЛА — ядро парсера.

Определяет 29 разделов по семантическим ключевым словам, а не по нумерации,
т.к. реальные документы ПМЛА имеют сломанную нумерацию (1.a.i, 1.11,
дубликаты номеров и т.д.).

Алгоритм:
1. Проход по всем параграфам с индексом, текстом, именем стиля, жирностью.
2. Пропуск пустых параграфов.
3. Проверка каждого непустого параграфа по регулярным выражениям.
4. Дедупликация по section_id — побеждает первое вхождение.
5. Вычисление end_para_idx для каждого раздела (следующий раздел или None).
6. Оценка полноты = найденные_обязательные / 14.
7. Валидность ПМЛА: полнота >= 0.8 AND title_page AND special_section.
8. Генерация предупреждений.

Используются только stdlib: dataclasses, re, typing.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from typing import NamedTuple

from src.infrastructure.rag.parsers.models import DetectedSection, DetectionReport

# ── Типы вспомогательные ────────────────────────────────────────────

class _PatternEntry(NamedTuple):
    """Запись паттерна: идентификатор раздела, регулярное выражение,
    каноническое название, уровень вложенности, ограничение на позицию."""
    section_id: str
    pattern: re.Pattern[str]
    title: str
    level: int
    max_para_idx: int | None  # если задано — принимать только до этого индекса


# ── Регулярные выражения для разделов ────────────────────────────────
# Флаги: IGNORECASE | UNICODE — поиск без учёта регистра и с поддержкой
# кириллических классов символов.

_FLAGS = re.IGNORECASE | re.UNICODE

# ── Обязательные разделы (14 основных + special_section) ─────────────

_PATTERNS: list[_PatternEntry] = [
    # Титульная страница — только в первых 15 параграфах
    # Основной паттерн: СОГЛАСОВАНО/УТВЕРЖДАЮ
    # Fallback: ПЛАН МЕРОПРИЯТИЙ ПО ЛОКАЛИЗАЦИИ И ЛИКВИДАЦИИ (заголовок документа)
    _PatternEntry(
        "title_page",
        re.compile(
            r"СОГЛАСОВАНО|УТВЕРЖДАЮ|"
            r"ПЛАН\s+МЕРОПРИЯТИЙ\s+ПО\s+ЛОКАЛИЗАЦИИ\s+И\s+ЛИКВИДАЦИИ",
            _FLAGS,
        ),
        "Титульная страница",
        1,
        15,
    ),
    # Журнал корректировки — только в первых 30 параграфах
    _PatternEntry(
        "correction_log",
        re.compile(
            r"ЖУРНАЛ\s+КОРРЕКТИРОВКИ",
            _FLAGS,
        ),
        "Журнал корректировки",
        1,
        30,
    ),
    # Содержание — только в первые 30 параграфов
    _PatternEntry(
        "toc",
        re.compile(
            r"^СОДЕРЖАНИЕ$",
            _FLAGS,
        ),
        "Содержание",
        1,
        30,
    ),
    # Обозначений и сокращений
    _PatternEntry(
        "abbreviations",
        re.compile(
            r"ОБОЗНАЧЕНИЙ\s+И\s+СОКРАЩЕНИЙ",
            _FLAGS,
        ),
        "Обозначения и сокращения",
        1,
        None,
    ),
    # Термины и определения
    _PatternEntry(
        "terms",
        re.compile(
            r"ТЕРМИНЫ\s+И\s+ОПРЕДЕЛЕНИЯ",
            _FLAGS,
        ),
        "Термины и определения",
        1,
        None,
    ),
    # Введение — точное слово, отдельно стоящее
    _PatternEntry(
        "introduction",
        re.compile(
            r"^ВВЕДЕНИЕ$",
            _FLAGS,
        ),
        "Введение",
        1,
        None,
    ),
    # Раздел 1 — Характеристика объекта
    # Допускаем слова между "Характеристика" и "объект" (например, "опасного производственного")
    _PatternEntry(
        "section_1",
        re.compile(
            r"Характеристик\w*.*объект\w*",
            _FLAGS,
        ),
        "Характеристика объекта",
        1,
        None,
    ),
    # Раздел 2 — Сценарии наиболее вероятных аварий
    _PatternEntry(
        "section_2",
        re.compile(
            r"Сценари\w*.*наиболее\s+вероятн",
            _FLAGS,
        ),
        "Сценарии наиболее вероятных аварийных ситуаций",
        1,
        None,
    ),
    # Раздел 3 — Характеристики аварийности и травматизма
    _PatternEntry(
        "section_3",
        re.compile(
            r"Характеристик\w*.*аварийност.*травматизм",
            _FLAGS,
        ),
        "Характеристика аварийности и травматизма",
        1,
        None,
    ),
    # Раздел 4 — Количество сил и средств локализации
    _PatternEntry(
        "section_4",
        re.compile(
            r"Количество.*сил\s+и\s+средств.*локализации",
            _FLAGS,
        ),
        "Количество сил и средств локализации",
        1,
        None,
    ),
    # Раздел 5 — Взаимодействие сил и средств
    _PatternEntry(
        "section_5",
        re.compile(
            r"Взаимодействи\w*.*сил\s+и\s+средств",
            _FLAGS,
        ),
        "Взаимодействие сил и средств",
        1,
        None,
    ),
    # Раздел 6 — Состав и дислокация сил и средств
    _PatternEntry(
        "section_6",
        re.compile(
            r"Состав\s+и\s+дислокация.*сил\s+и\s+средств",
            _FLAGS,
        ),
        "Состав и дислокация сил и средств",
        1,
        None,
    ),
    # Раздел 7 — Готовность сил и средств локализации
    _PatternEntry(
        "section_7",
        re.compile(
            r"готовност\w*.*сил\s+и\s+средств.*локализации",
            _FLAGS,
        ),
        "Готовность сил и средств локализации",
        1,
        None,
    ),
    # Раздел 8 — Управления, связи и оповещения
    _PatternEntry(
        "section_8",
        re.compile(
            r"управления,?\s*связи"
            r"|управления.*связи.*оповещени",
            _FLAGS,
        ),
        "Управления, связи и оповещения",
        1,
        None,
    ),
    # Раздел 9 — Обмен информацией (упрощённый паттерн)
    # Реальный текст: "Взаимный обмен информацией о ЧС(Н)"
    _PatternEntry(
        "section_9",
        re.compile(
            r"(?:взаимн\w*\s+)?обмен\s+информаци",
            _FLAGS,
        ),
        "Система взаимного обмена информацией",
        1,
        None,
    ),
    # Раздел 10 — Первоочередные действия (упрощённый паттерн)
    # Реальный текст: "10. Первоочередные действия при получении сигнала об авариях"
    _PatternEntry(
        "section_10",
        re.compile(
            r"Первоочередн\w*.*действия",
            _FLAGS,
        ),
        "Первоочередные действия по локализации",
        1,
        None,
    ),
    # Раздел 11 — Действия производственного персонала
    _PatternEntry(
        "section_11",
        re.compile(
            r"Действия.*производственн\w*.*персонала",
            _FLAGS,
        ),
        "Действия производственного персонала",
        1,
        None,
    ),
    # Раздел 12 — Мероприятия по безопасности населения
    _PatternEntry(
        "section_12",
        re.compile(
            r"Мероприятия.*безопасност\w*.*населения",
            _FLAGS,
        ),
        "Мероприятия по безопасности населения",
        1,
        None,
    ),
    # Раздел 13 — Материально-техническое обеспечение
    _PatternEntry(
        "section_13",
        re.compile(
            r"материально-техническ\w*.*обеспечения",
            _FLAGS,
        ),
        "Материально-техническое обеспечение",
        1,
        None,
    ),
    # Специальный раздел
    _PatternEntry(
        "special_section",
        re.compile(
            r"Специальный\s+раздел",
            _FLAGS,
        ),
        "Специальный раздел",
        1,
        None,
    ),
    # ── Приложения (упрощённые паттерны — только "Приложение N") ──────
    # В реальных документах описание приложения на следующей строке
    _PatternEntry(
        "appendix_1",
        re.compile(
            r"Приложение\s+[№#]?\s*1\b",
            _FLAGS,
        ),
        "Приложение 1",
        1,
        None,
    ),
    _PatternEntry(
        "appendix_2",
        re.compile(
            r"Приложение\s+[№#]?\s*2\b",
            _FLAGS,
        ),
        "Приложение 2",
        1,
        None,
    ),
    _PatternEntry(
        "appendix_3",
        re.compile(
            r"Приложение\s+[№#]?\s*3\b",
            _FLAGS,
        ),
        "Приложение 3",
        1,
        None,
    ),
    _PatternEntry(
        "appendix_4",
        re.compile(
            r"Приложение\s+[№#]?\s*4\b",
            _FLAGS,
        ),
        "Приложение 4",
        1,
        None,
    ),
    _PatternEntry(
        "appendix_5",
        re.compile(
            r"Приложение\s+[№#]?\s*5\b",
            _FLAGS,
        ),
        "Приложение 5",
        1,
        None,
    ),
    # ── Служебные разделы ────────────────────────────────────────
    _PatternEntry(
        "bibliography",
        re.compile(
            r"СПИСОК.*ЛИТЕРАТУРЫ",
            _FLAGS,
        ),
        "Список литературы",
        1,
        None,
    ),
    _PatternEntry(
        "familiarization",
        re.compile(
            r"ЛИСТ\s+ОЗНАКОМЛЕНИЯ",
            _FLAGS,
        ),
        "Лист ознакомления",
        1,
        None,
    ),
]

# Обязательные section_id для оценки полноты (14 основных + special_section)
_REQUIRED_IDS: frozenset[str] = frozenset(
    {
        "section_1", "section_2", "section_3", "section_4",
        "section_5", "section_6", "section_7", "section_8",
        "section_9", "section_10", "section_11", "section_12",
        "section_13",
        "special_section",
    }
)

# Предупреждаемые section_id — разделы, отсутствие которых заслуживает
# предупреждения, но не является критическим.
_WARNING_IF_MISSING: frozenset[str] = frozenset(
    {
        "title_page",
        "correction_log",
        "toc",
        "abbreviations",
        "terms",
        "introduction",
        "appendix_1", "appendix_2", "appendix_3", "appendix_4", "appendix_5",
        "bibliography",
        "familiarization",
    }
)

# Разделы, которые не должны детектироваться в区域内 содержания (ТОС).
# Эти слова появляются в оглавлении, но не являются реальными заголовками.
_TOC_PARAGRAPH_PATTERNS = [
    re.compile(r"^\d+\s+[А-Я]"),  # "1 Характеристика..." в оглавлении
    re.compile(r"^\d+\.\s*[А-Я]"),  # "1. Характеристика..." в оглавлении
]


# ── Вспомогательные функции ──────────────────────────────────────────

def _build_section_map() -> dict[str, _PatternEntry]:
    """Строит словарь section_id → _PatternEntry для быстрого доступа."""
    return {entry.section_id: entry for entry in _PATTERNS}


def _detect_unusual_numbering(text: str) -> bool:
    """Проверяет, содержит ли текст нумерацию, отличающуюся от простой
    римской/арабской (например, '1.a.i', '1.11', дублирующиеся номера).

    Возвращает True, если обнаружена подозрительная нумерация.
    """
    # Паттерны подозрительных нумераций
    suspicious = [
        re.compile(r"^\d+\.[a-z]+\.\d+", re.IGNORECASE),       # 1.a.1
        re.compile(r"^\d+\.\d{2,}(?!\.\d)"),                    # 1.11 (не 1.1.1)
        re.compile(r"^\d+\.[a-z]+\.[a-z]+\.\d+", re.IGNORECASE), # 1.a.i.1
    ]
    return any(p.search(text.strip()) for p in suspicious)


def _is_numbered_heading(text: str) -> bool:
    """Проверяет, является ли текст пронумерованным заголовком.

    Примеры: '1. Название', '1.1 Название', 'Приложение 1'
    """
    return bool(re.match(
        r"^(?:\d+(?:\.\d+)*\.?\s|Приложение\s+\d+)",
        text.strip(),
        re.IGNORECASE,
    ))


def _is_in_toc_region(
    para_list: list[tuple[str, str | None, bool]],
    para_idx: int,
    toc_start: int | None,
    toc_end: int | None,
) -> bool:
    """Проверяет, находится ли параграф в区域内 содержания (ТОС).

    Если ТОС найден, возвращает True для параграфов между toc_start и toc_end.
    """
    if toc_start is None or toc_end is None:
        return False
    return toc_start <= para_idx < toc_end


# ── Основной класс ───────────────────────────────────────────────────

class SectionDetector:
    """Детектор разделов ПМЛА по семантическим ключевым словам.

    Использует набор из 29 регулярных выражений для поиска разделов
    плана мероприятия по ликвидации аварий. Подход основан на
    семантических маркерах, а не на нумерации, что обеспечивает
    устойчивость к дефектам реальных документов.

    Пример использования::

        detector = SectionDetector()
        paragraphs = [("СОГЛАСОВАНО", None, True), ...]
        report = detector.detect(paragraphs)
        if report.is_valid_pmla:
            print(f"Найдено {len(report.detected_sections)} разделов")
    """

    def __init__(self) -> None:
        """Инициализирует детектор и строит карту паттернов."""
        self._pattern_map: dict[str, _PatternEntry] = _build_section_map()
        # Сохраняем порядок для детерминированного прохода
        self._pattern_list: list[_PatternEntry] = list(_PATTERNS)

    # ── Публичное API ────────────────────────────────────────────

    def detect(
        self,
        paragraphs: Iterable[tuple[str, str | None, bool]],
    ) -> DetectionReport:
        """Основной метод разметки документа.

        Args:
            paragraphs: Итерируемый список кортежей
                (текст, имя_стиля, жирный_шрифт).

        Returns:
            DetectionReport с найденными разделами, полнотой
            и предупреждениями.
        """
        return self.detect_with_source(paragraphs, source_path="")

    def detect_with_source(
        self,
        paragraphs: Iterable[tuple[str, str | None, bool]],
        source_path: str,
    ) -> DetectionReport:
        """Разметка с указанием пути к исходному файлу.

        Args:
            paragraphs: Итерируемый список кортежей
                (текст, имя_стиля, жирный_шрифт).
            source_path: Путь к файлу-источнику (для отчёта).

        Returns:
            DetectionReport с полной информацией о найденных разделах.
        """
        # Конвертируем в список для многократного прохода
        para_list = list(paragraphs)
        total = len(para_list)

        # Словарь section_id → (DetectedSection, номер_паттерна_для_отладки)
        found: dict[str, DetectedSection] = {}
        warnings: list[str] = []
        seen_matches: dict[str, list[int]] = {}  # section_id → [para_idx, ...]

        # ── Найти границы содержания (ТОС) ────────────────────────
        toc_start: int | None = None
        toc_end: int | None = None
        for i, (text, _style, _bold) in enumerate(para_list[:50]):
            if text and text.strip() == "СОДЕРЖАНИЕ":
                toc_start = i
            elif toc_start is not None and i > toc_start + 2:
                # Ищем конец содержания — строку с номером страницы или пустую строку
                if not text or not text.strip():
                    toc_end = i
                    break
                # Или если нашли заголовок раздела (не в формате оглавления)
                if _is_numbered_heading(text.strip()) and not re.match(
                    r"^\d+\s", text.strip()
                ):
                    toc_end = i
                    break
        # Если не нашли конец содержания, ограничиваем 30 параграфами
        if toc_start is not None and toc_end is None:
            toc_end = min(toc_start + 30, total)

        # ── Основной проход ──────────────────────────────────────

        for para_idx, (text, style_name, is_bold) in enumerate(para_list):
            # Пропуск пустых параграфов
            if not text or not text.strip():
                continue

            stripped = text.strip()

            # Пропуск параграфов в区域内 содержания (ТОС)
            if _is_in_toc_region(para_list, para_idx, toc_start, toc_end):
                continue

            # Проверка каждого паттерна
            for entry in self._pattern_list:
                # Если раздел уже найден — пропускаем (первое вхождение)
                if entry.section_id in found:
                    continue

                # Проверка ограничения на позицию
                if (
                    entry.max_para_idx is not None
                    and para_idx > entry.max_para_idx
                ):
                    continue

                # Поиск совпадения
                if entry.pattern.search(stripped):
                    # Фиксируем совпадение
                    confidence = self._compute_confidence(
                        entry, stripped, style_name, is_bold,
                    )

                    section = DetectedSection(
                        section_id=entry.section_id,
                        title=entry.title,
                        level=entry.level,
                        start_para_idx=para_idx,
                        end_para_idx=None,  # заполним позже
                        confidence=confidence,
                        match_pattern=entry.pattern.pattern,
                    )
                    found[entry.section_id] = section

                    # Трекаем для дедупликации
                    if entry.section_id not in seen_matches:
                        seen_matches[entry.section_id] = []
                    seen_matches[entry.section_id].append(para_idx)

                    # Предупреждение о подозрительной нумерации
                    if _detect_unusual_numbering(stripped):
                        warnings.append(
                            f"Подозрительная нумерация в параграфе {para_idx}: "
                            f"'{stripped[:80]}...'"
                        )

                    # Одно совпадение на параграф — достаточно
                    break

        # ── Предупреждения о дубликатах ───────────────────────────
        for section_id, indices in seen_matches.items():
            if len(indices) > 1:
                warnings.append(
                    f"Дублирующееся вхождение '{section_id}' "
                    f"в параграфах {indices}. Используется первое."
                )

        # ── Вычисление end_para_idx ───────────────────────────────
        self._compute_end_indices(found, total)

        # ── Проверка нумерации разделов ───────────────────────────
        self._check_numbering(para_list, found, warnings)

        # ── Оценка полноты ────────────────────────────────────────
        found_required = [
            sid for sid in _REQUIRED_IDS if sid in found
        ]
        completeness = len(found_required) / len(_REQUIRED_IDS) if _REQUIRED_IDS else 0.0

        # ── Отсутствующие разделы ─────────────────────────────────
        missing = [sid for sid in sorted(_REQUIRED_IDS) if sid not in found]

        # Предупреждения об отсутствующих служебных разделах
        for sid in sorted(_WARNING_IF_MISSING):
            if sid not in found:
                entry = self._pattern_map[sid]
                warnings.append(
                    f"Не найден служебный раздел: {entry.title} ({sid})"
                )

        # ── Валидность ПМЛА ──────────────────────────────────────
        is_valid = (
            completeness >= 0.8
            and "title_page" in found
            and "special_section" in found
        )

        # ── Формирование отчёта ──────────────────────────────────
        sections_list = list(found.values())
        sections_list.sort(key=lambda s: s.start_para_idx)

        return DetectionReport(
            source_path=source_path,
            total_paragraphs=total,
            detected_sections=sections_list,
            missing_sections=missing,
            completeness_score=completeness,
            is_valid_pmla=is_valid,
            warnings=warnings,
        )

    # ── Вспомогательные методы ───────────────────────────────────

    def _compute_confidence(
        self,
        entry: _PatternEntry,
        text: str,
        style_name: str | None,
        is_bold: bool,
    ) -> float:
        """Вычисляет уровень уверенности в найденном совпадении.

        Факторы:
        - Жирный шрифт и заголовочный стиль → +0.1
        - Начало параграфа совпадает с паттерном → +0.1
        - Наличие нумерации → +0.05
        - Длина текста (короткий текст = заголовок) → +0.05

        Returns:
            Значение от 0.0 до 1.0.
        """
        confidence = 0.7  # базовый уровень для семантического совпадения

        # Заголовочный стиль
        if is_bold:
            confidence += 0.1

        if style_name and (
            "heading" in style_name.lower()
            or "заголовок" in style_name.lower()
            or "title" in style_name.lower()
            or "header" in style_name.lower()
        ):
            confidence += 0.1

        # Паттерн в начале строки
        if entry.pattern.search(text[:50]):
            confidence += 0.1

        # Наличие нумерации перед заголовком
        if _is_numbered_heading(text):
            confidence += 0.05

        # Короткий текст — скорее всего заголовок
        if len(text.strip()) < 80:
            confidence += 0.05

        return min(confidence, 1.0)

    def _compute_end_indices(
        self,
        found: dict[str, DetectedSection],
        total: int,
    ) -> None:
        """Вычисляет end_para_idx для каждого найденного раздела.

        Значение end_para_idx — это индекс первого параграфа следующего
        раздела. Для последнего раздела — None (до конца документа).
        """
        if not found:
            return

        # Сортируем по start_para_idx
        sorted_sections = sorted(found.values(), key=lambda s: s.start_para_idx)

        for i, section in enumerate(sorted_sections):
            if i + 1 < len(sorted_sections):
                section.end_para_idx = sorted_sections[i + 1].start_para_idx
            else:
                section.end_para_idx = None  # до конца документа

    def _check_numbering(
        self,
        para_list: list[tuple[str, str | None, bool]],
        found: dict[str, DetectedSection],
        warnings: list[str],
    ) -> None:
        """Проверяет нумерацию разделов на предмет дубликатов и пропусков.

        Анализирует первые 100 параграфов на наличие пронумерованных
        заголовков и проверяет непрерывность последовательности.
        """
        # Собираем номера разделов из первых 100 параграфов
        section_numbers: list[tuple[int, int]] = []  # (номер, индекс_параграфа)

        for para_idx, (text, _style, _bold) in enumerate(para_list[:100]):
            if not text or not text.strip():
                continue

            stripped = text.strip()
            match = re.match(r"^(\d+)\s*[.\)]", stripped)
            if match:
                num = int(match.group(1))
                section_numbers.append((num, para_idx))

        if not section_numbers:
            return

        # Проверка на дубликаты номеров
        seen_nums: dict[int, list[int]] = {}
        for num, idx in section_numbers:
            if num not in seen_nums:
                seen_nums[num] = []
            seen_nums[num].append(idx)

        for num, indices in seen_nums.items():
            if len(indices) > 1:
                warnings.append(
                    f"Дублирующийся номер раздела '{num}' "
                    f"в параграфах {indices}"
                )

        # Проверка на пропуски в последовательности
        nums = sorted(seen_nums.keys())
        if nums:
            min_num = min(nums)
            max_num = max(nums)
            expected = set(range(min_num, max_num + 1))
            actual = set(nums)
            missing_nums = expected - actual
            if missing_nums:
                warnings.append(
                    f"Пропущены номера разделов: {sorted(missing_nums)}"
                )
