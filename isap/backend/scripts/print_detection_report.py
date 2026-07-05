"""Вывод отчёта детекции разделов ПМЛА в читаемом формате."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.infrastructure.rag.structural_pipeline import parse_pmla_docx
from src.infrastructure.rag.parsers.models import DetectionReport


def print_detection_report(report: DetectionReport, verbose: bool = False) -> None:
    """Красивый вывод отчёта детекции разделов.

    Args:
        report: Отчёт детектора.
        verbose: Показать подробности по каждому разделу.
    """
    print(f"\n{'='*70}")
    print(f"ОТЧЁТ ДЕТЕКЦИИ РАЗДЕЛОВ ПМЛА")
    print(f"{'='*70}")
    print(f"Файл: {report.source_path}")
    print(f"Параграфов: {report.total_paragraphs}")
    print(f"Найдено разделов: {len(report.detected_sections)}")
    print(f"Completeness: {report.completeness_score:.0%}")
    print(f"Валидный ПМЛА: {'Да' if report.is_valid_pmla else 'Нет'}")

    if report.missing_sections:
        print(f"\nОтсутствующие обязательные разделы ({len(report.missing_sections)}):")
        for s in report.missing_sections:
            print(f"  ✗ {s}")

    if report.warnings:
        print(f"\nПредупреждения ({len(report.warnings)}):")
        for w in report.warnings:
            print(f"  ⚠ {w}")

    print(f"\nНайденные разделы:")
    for s in sorted(report.detected_sections, key=lambda x: x.start_para_idx):
        end = s.end_para_idx if s.end_para_idx is not None else "конец"
        span = f"параграфы {s.start_para_idx}–{end}"
        print(f"  [{s.section_id:25s}] {s.title}")
        if verbose:
            print(f"    {span}, confidence={s.confidence:.2f}")


def print_chunks_summary(chunks: list, verbose: bool = False) -> None:
    """Вывод сводки по чанкам.

    Args:
        chunks: Список StructuralChunk.
        verbose: Показать превью содержимого.
    """
    print(f"\n{'='*70}")
    print(f"СВОДКА ПО ЧАНКАМ")
    print(f"{'='*70}")
    print(f"Всего чанков: {len(chunks)}")

    # Группировка по section_id
    by_section: dict[str, list] = {}
    for chunk in chunks:
        by_section.setdefault(chunk.section_id, []).append(chunk)

    print(f"\nПо разделам:")
    for sid in sorted(by_section.keys()):
        section_chunks = by_section[sid]
        total_chars = sum(len(c.content) for c in section_chunks)
        print(f"  {sid:25s} — {len(section_chunks):2d} чанков, {total_chars:6d} символов")
        if verbose and section_chunks:
            preview = section_chunks[0].content[:100].replace("\n", " ")
            print(f"    Превью: {preview}...")


def test_print_detection_report() -> None:
    """Тестовый запуск: парсит эталонный образец и выводит отчёт."""
    import sys
    from pathlib import Path

    # Ищем образец
    samples_dir = Path("src/uploads/pmla_samples")
    if not samples_dir.exists():
        print("Директория образцов не найдена")
        return

    docx_files = list(samples_dir.glob("*.docx"))
    if not docx_files:
        print("Нет DOCX файлов")
        return

    # Берём первый подходящий (не тестовый)
    target = None
    for f in docx_files:
        if "СПК" in f.name or "ПМЛА" in f.name:
            target = f
            break
    if not target:
        target = docx_files[0]

    print(f"Обработка: {target.name}")

    result = parse_pmla_docx(str(target))
    print_detection_report(result.report, verbose=True)
    print_chunks_summary(result.chunks, verbose=True)


if __name__ == "__main__":
    test_print_detection_report()
