FROM python:3.12.7-slim

WORKDIR /app

# Установи зависимости системы
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    wireguard-tools \
    && rm -rf /var/lib/apt/lists/*

# Копируй requirements
COPY requirements.txt .

# Установи Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируй код
COPY . .

# Открой порт
EXPOSE 8080

# Запусти Python напрямую
CMD ["python3", "server.py"]
