"""Загрузка начальных данных реестра нормативных документов."""
import asyncio
import json
from pathlib import Path

from src.infrastructure.database.engine import async_session_factory
from src.infrastructure.repositories.regulatory_repo import RegulatoryRepository

DATA_FILE = Path(__file__).parent.parent / "data" / "regulatory_initial.json"


async def load():
    async with async_session_factory() as session:
        repo = RegulatoryRepository(session)
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))

        existing = await repo.get_multi(limit=1000)
        existing_titles = {d.title for d in existing}

        loaded = 0
        for item in data:
            if item["title"] not in existing_titles:
                await repo.create(item)
                loaded += 1
                print(f"  + {item['title'][:80]}...")
            else:
                print(f"  = {item['title'][:80]}... (уже есть)")

        print(f"\nЗагружено: {loaded} из {len(data)}")


if __name__ == "__main__":
    asyncio.run(load())
