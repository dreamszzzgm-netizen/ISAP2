"""Роутер загрузки корпуса знаний в ChromaDB."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.infrastructure.rag.corpus_loader import CorpusLoader, LoadResult

router = APIRouter()


class LoadResponse(BaseModel):
    regulatory_loaded: int
    pmla_loaded: int
    files_loaded: int
    total_chunks: int
    errors: list[str] | None = None


@router.post("/load", response_model=LoadResponse)
async def load_corpus():
    """Загрузить корпус знаний в ChromaDB (нормативы + ПМЛА + файлы)."""
    try:
        loader = CorpusLoader()
        result = await loader.load_all()
        return LoadResponse(
            regulatory_loaded=result.regulatory_loaded,
            pmla_loaded=result.pmla_loaded,
            files_loaded=result.files_loaded,
            total_chunks=result.total_chunks,
            errors=result.errors,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки корпуса: {e}")


@router.get("/stats")
async def corpus_stats():
    """Статистика коллекции ChromaDB."""
    try:
        import chromadb
        from src.core.settings import settings

        client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        collection = client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        count = collection.count()
        return {"collection": settings.chroma_collection_name, "total_chunks": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ChromaDB недоступен: {e}")
