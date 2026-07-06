"""Тест генерации ПМЛА на реальном кейсе."""
import asyncio
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def test_generation():
    """Тест генерации ПМЛА для газораспределительной станции."""
    from src.infrastructure.rag.structural_pipeline import StructuralSampleRetriever
    from src.infrastructure.rag.structural_pipeline import parse_pmla_docx
    from src.infrastructure.rag.sample_indexer import SAMPLES_COLLECTION
    from src.infrastructure.rag.pipeline import VectorStore

    print("=" * 70)
    print("ТЕСТ ГЕНЕРАЦИИ ПМЛА")
    print("=" * 70)

    # 1. Проверяем индекс
    store = VectorStore(collection_name=SAMPLES_COLLECTION)
    print(f"\nЧанков в индексе: {store._collection.count()}")

    # 2. Тестируем поиск по разделам
    retriever = StructuralSampleRetriever()

    test_queries = [
        ("section_1", "характеристика объекта газопотребления"),
        ("section_2", "сценарии аварий газопровод утечка"),
        ("section_5", "взаимодействие сил ликвидация аварий"),
        ("section_10", "первоочередные действия при аварии"),
        ("special_section", "оперативные действия ликвидация аварий"),
    ]

    print("\n" + "=" * 70)
    print("ТЕСТ RAG-ПОИСКА ПО РАЗДЕЛАМ")
    print("=" * 70)

    for section_id, query in test_queries:
        chunks = await retriever.retrieve_by_section(
            query=query,
            section_id=section_id,
            top_k=2,
        )
        print(f"\n[{section_id}] Запрос: {query}")
        print(f"  Найдено чанков: {len(chunks)}")
        for i, chunk in enumerate(chunks):
            preview = chunk.content[:80].replace("\n", " ")
            print(f"  Чанк {i}: {len(chunk.content)} символов")
            print(f"    {preview}...")

    # 3. Тестируем извлечение few-shot из образца
    print("\n" + "=" * 70)
    print("ТЕСТ FEW-SHOT ИЗВЛЕЧЕНИЯ")
    print("=" * 70)

    result = parse_pmla_docx("src/uploads/pmla_samples/20260704_063105_ПМЛА ООО СПК ААА.docx")

    for section in result.report.detected_sections[:5]:
        # Извлекаем текст раздела
        start = section.start_para_idx
        end = section.end_para_idx if section.end_para_idx is not None else len(result.paragraphs)

        section_text = []
        for i in range(start, end):
            if i < len(result.paragraphs):
                text = result.paragraphs[i][0]
                if text and text.strip():
                    section_text.append(text.strip())

        if section_text:
            preview = " ".join(section_text)[:150].replace("\n", " ")
            print(f"\n[{section.section_id}] {section.title}")
            print(f"  Параграфы {start}–{end}, {len(section_text)} абзацев")
            print(f"  Превью: {preview}...")

    print("\n" + "=" * 70)
    print("ТЕСТ ЗАВЕРШЁН")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_generation())
