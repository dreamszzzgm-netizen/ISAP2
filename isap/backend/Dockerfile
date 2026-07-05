FROM python:3.11-slim

WORKDIR /app

# Системные зависимости: PyMuPDF, asyncpg, шрифты, LibreOffice (конвертация PDF)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    fonts-dejavu-core \
    fonts-liberation \
    fonts-freefont-ttf \
    libreoffice-core \
    libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости
COPY pyproject.toml .

# Устанавливаем pip и зависимости
RUN pip install --upgrade pip && \
    pip install -e ".[dev]"

# Копируем исходники
COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
