"""Переиндексация образцов ПМЛА через структурный RAG-пайплайн.

Индексирует DOCX файлы напрямую (без БД).
"""
import asyncio
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.infrastructure.rag.structural_pipeline import (
    StructuralSampleIndexer,
    parse_pmla_docx,
)
from src.infrastructure.rag.pipeline import VectorStore
from src.infrastructure.rag.sample_indexer import SAMPLES_COLLECTION


async def reindex_samples(samples_dir: str):
    """Переиндексирует все DOCX файлы в директории."""
    samples_path = Path(samples_dir)
    if not samples_path.exists():
        print(f"Директория не найдена: {samples_dir}")
        return

    docx_files = list(samples_path.glob("*.docx"))
    if not docx_files:
        print(f"Нет DOCX файлов в {samples_dir}")
        return

    # Очищаем коллекцию
    store = VectorStore(collection_name=SAMPLES_COLLECTION)
    store.delete(where={})
    print(f"Коллекция {SAMPLES_COLLECTION} очищена")

    indexer = StructuralSampleIndexer()
    total_chunks = 0

    for docx_file in sorted(docx_files):
        # Пропускаем тестовые файлы
        if "test" in docx_file.name.lower():
            print(f"Пропуск тестового файла: {docx_file.name}")
            continue

        print(f"\nОбработка: {docx_file.name}")
        try:
            # Парсим и показываем отчёт
            result = parse_pmla_docx(str(docx_file))
            print(f"  Разделов: {len(result.report.detected_sections)}")
            print(f"  Чанков: {len(result.chunks)}")
            print(f"  Completeness: {result.report.completeness_score:.0%}")

            # Индексируем с фиктивным sample_id
            sample_id = uuid4()
            chunks_count = await indexer.index_sample(
                sample_id=sample_id,
                file_path=str(docx_file),
                file_type="docx",
                facility_type="сеть газопотребления",
                hazard_class="3",
            )
            total_chunks += chunks_count
            print(f"  Проиндексировано: {chunks_count} чанков")
        except Exception as e:
            print(f"  Ошибка: {e}")

    print(f"\n{'='*50}")
    print(f"ИТОГО: проиндексировано {total_chunks} чанков")


async def verify_index():
    """Проверяет индексацию — ищет чанки с section_id."""
    from src.infrastructure.rag.structural_pipeline import StructuralSampleRetriever

    retriever = StructuralSampleRetriever()

    chunks = await retriever.retrieve_by_section(
        query='сценарии аварий',
        section_id='section_2',
        top_k=3,
    )

    print(f"\nНайдено чанков для section_2: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        sid = chunk.metadata.get('section_id', '?')
        print(f"  Чанк {i}: section_id={sid}, {len(chunk.content)} символов")
        print(f"    Превью: {chunk.content[:100]}...")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "reindex"
    samples_dir = sys.argv[2] if len(sys.argv) > 2 else "src/uploads/pmla_samples"

    if action == "reindex":
        asyncio.run(reindex_samples(samples_dir))
    elif action == "verify":
        asyncio.run(verify_index())
    else:
        print("Использование: python reindex_samples.py [reindex|verify] [dir]")
