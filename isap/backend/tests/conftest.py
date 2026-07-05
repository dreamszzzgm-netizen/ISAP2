"""Общие фикстуры для тестов — отключают auth middleware."""
import os

# Отключаем API Key auth для всех тестов (middleware пропускает запросы при пустом ключе)
os.environ["API_KEY"] = ""
