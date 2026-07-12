# Используем NVIDIA CUDA + Python образ для GPU-ускорения
# При первом запуске потребуется авторизация в NGC registry:
#   docker login nvcr.io
# Username: $oauthtoken
# Password: ваш NGC_API_KEY
FROM nvcr.io/nvidia/cuda:12.4.0-runtime-ubuntu22.04

WORKDIR /app

# Устанавливаем Python 3.11 и системные зависимости
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-distutils \
    python3-pip \
    gcc \
    libpq-dev \
    fonts-dejavu-core \
    fonts-liberation \
    fonts-freefont-ttf \
    libreoffice-core \
    libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

# Настраиваем python3.11 как python по умолчанию
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Копируем зависимости
COPY pyproject.toml .

# Устанавливаем pip и зависимости
RUN pip install --upgrade pip && \
    pip install -e ".[dev]"

# Копируем исходники
COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
