"""Общие фикстуры для тестов — отключают auth middleware."""
import os
from pathlib import Path

# Отключаем API Key auth для всех тестов (middleware пропускает запросы при пустом ключе)
os.environ["API_KEY"] = ""

# Use a local temp dir to avoid Windows permission errors on system temp
_local_tmp = Path(__file__).resolve().parent.parent / ".pytest_tmp"
_local_tmp.mkdir(exist_ok=True)
os.environ["TMPDIR"] = str(_local_tmp)
