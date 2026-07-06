"""CLI-скрипт загрузки корпуса знаний в ChromaDB.

Использование:
    cd backend
    python -m scripts.load_corpus
"""
import asyncio
import logging
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from src.infrastructure.rag.corpus_loader import CorpusLoader

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


async def main():
    print("=== Загрузка корпуса знаний в ChromaDB ===\n")

    loader = CorpusLoader()
    result = await loader.load_all()

    print(f"\nРезультат:")
    print(f"  Нормативов из БД: {result.regulatory_loaded}")
    print(f"  ПМЛА из БД:       {result.pmla_loaded}")
    print(f"  Файлов:           {result.files_loaded}")
    print(f"  Всего чанков:     {result.total_chunks}")

    if result.errors:
        print(f"\nОшибки:")
        for err in result.errors:
            print(f"  - {err}")
    else:
        print("\nОшибок нет.")


if __name__ == "__main__":
    asyncio.run(main())
