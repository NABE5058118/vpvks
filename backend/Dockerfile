FROM python:3.12.7-slim

WORKDIR /app

# Установи зависимости системы
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируй requirements
COPY requirements.txt .

# Установи Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируй код
COPY . .

# Копируем скрипт включения Marzban inbound
COPY enable_marzban_inbounds.py /app/enable_marzban_inbounds.py

# Открой порт
EXPOSE 8080

# Запусти Python напрямую
CMD ["python3", "server.py"]
