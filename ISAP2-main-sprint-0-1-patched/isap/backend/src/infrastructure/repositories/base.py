from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: UUID) -> ModelType | None:
        result = await self.session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
    ) -> list[ModelType]:
        query = select(self.model)
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, obj_data: dict[str, Any]) -> ModelType:
        obj = self.model(**obj_data)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def update(self, id: UUID, obj_data: dict[str, Any]) -> ModelType | None:
        obj = await self.get(id)
        if obj is None:
            return None
        for key, value in obj_data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def delete(self, id: UUID) -> bool:
        obj = await self.get(id)
        if obj is None:
            return False
        await self.session.delete(obj)
        await self.session.commit()
        return True

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        from sqlalchemy import func

        query = select(func.count()).select_from(self.model)
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        result = await self.session.execute(query)
        return result.scalar_one()
