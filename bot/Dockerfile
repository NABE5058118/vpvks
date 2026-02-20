FROM python:3.12.7-slim

WORKDIR /app

# Копируй requirements
COPY requirements.txt .

# Установи Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируй код
COPY . .

# Запусти Python напрямую
CMD ["python3", "main.py"]
