"""Репозиторий образцов ПМЛА."""
from src.infrastructure.database.models import PmlaSampleModel
from src.infrastructure.repositories.base import BaseRepository


class PmlaSampleRepository(BaseRepository[PmlaSampleModel]):
    def __init__(self, session):
        super().__init__(PmlaSampleModel, session)
