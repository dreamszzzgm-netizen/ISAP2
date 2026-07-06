"""Аудит образцов ПМЛА — проверка структурного RAG-пайплайна."""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.infrastructure.rag.structural_pipeline import parse_pmla_docx
from src.infrastructure.rag.parsers.models import DetectionReport
from src.infrastructure.rag.parsers.chunker import StructuralChunk


def print_report(report: DetectionReport, chunks: list[StructuralChunk], verbose: bool = False) -> None:
    """Красивый вывод отчёта."""
    print(f"\n{'='*70}")
    print(f"Файл: {report.source_path}")
    print(f"Параграфов: {report.total_paragraphs}")
    print(f"Разделов: {len(report.detected_sections)}")
    print(f"Чанков: {len(chunks)}")
    print(f"Completeness: {report.completeness_score:.0%}")
    print(f"Валидный ПМЛА: {'Да' if report.is_valid_pmla else 'Нет'}")

    if report.warnings:
        print(f"\nПредупреждения ({len(report.warnings)}):")
        for w in report.warnings[:5]:  # ограничиваем 5
            print(f"  ⚠ {w}")
        if len(report.warnings) > 5:
            print(f"  ... и ещё {len(report.warnings) - 5}")

    if report.missing_sections:
        print(f"\nОтсутствующие разделы ({len(report.missing_sections)}):")
        for s in report.missing_sections:
            print(f"  ✗ {s}")

    if verbose:
        print(f"\nНайденные разделы:")
        for s in sorted(report.detected_sections, key=lambda x: x.start_para_idx):
            end = s.end_para_idx if s.end_para_idx is not None else "конец"
            print(f"  [{s.section_id:25s}] {s.title}")
            print(f"    параграфы {s.start_para_idx}–{end}, confidence={s.confidence:.2f}")

        print(f"\nЧанки по разделам:")
        by_section: dict[str, list[StructuralChunk]] = {}
        for chunk in chunks:
            by_section.setdefault(chunk.section_id, []).append(chunk)
        for sid in sorted(by_section.keys()):
            section_chunks = by_section[sid]
            total_chars = sum(len(c.content) for c in section_chunks)
            print(f"  {sid:25s} — {len(section_chunks):2d} чанков, {total_chars:6d} символов")


def main():
    """Точка входа."""
    if len(sys.argv) < 2:
        print("Использование: python -m scripts.audit_samples <samples_dir> [--verbose]")
        print("  samples_dir — папка с .docx файлами образцов ПМЛА")
        sys.exit(1)

    samples_dir = Path(sys.argv[1])
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    if not samples_dir.exists():
        print(f"Директория не найдена: {samples_dir}")
        sys.exit(1)

    docx_files = list(samples_dir.glob("*.docx"))
    if not docx_files:
        print(f"В директории {samples_dir} нет .docx файлов")
        sys.exit(1)

    print(f"Найдено {len(docx_files)} DOCX файлов в {samples_dir}")

    results = []

    for docx_file in sorted(docx_files):
        try:
            result = parse_pmla_docx(str(docx_file))
            results.append(result)
            print_report(result.report, result.chunks, verbose)
        except Exception as e:
            print(f"\nОшибка при обработке {docx_file.name}: {e}")

    # Summary
    if not results:
        print("\nНет результатов для анализа")
        return

    valid_count = sum(1 for r in results if r.report.is_valid_pmla)
    avg_completeness = sum(r.report.completeness_score for r in results) / len(results)
    high_quality = sum(1 for r in results if r.report.completeness_score >= 0.8)
    total_chunks = sum(len(r.chunks) for r in results)

    print(f"\n{'='*70}")
    print(f"ИТОГО АУДИТА")
    print(f"{'='*70}")
    print(f"Всего образцов: {len(results)}")
    print(f"Валидных ПМЛА: {valid_count} ({valid_count/len(results):.0%})")
    print(f"Средняя полнота: {avg_completeness:.0%}")
    print(f">= 80% полноты: {high_quality} ({high_quality/len(results):.0%})")
    print(f"Всего чанков: {total_chunks}")

    # Coverage by section
    section_counts = {}
    for r in results:
        for s in r.report.detected_sections:
            section_counts[s.section_id] = section_counts.get(s.section_id, 0) + 1

    print(f"\nПокрытие по разделам:")
    for sid in sorted(section_counts.keys()):
        count = section_counts[sid]
        pct = count / len(results)
        bar = "█" * int(pct * 20)
        print(f"  {sid:25s} {count:3d}/{len(results)} ({pct:.0%}) {bar}")


if __name__ == "__main__":
    main()
