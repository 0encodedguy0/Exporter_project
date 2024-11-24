# Используем образ python 3.12
FROM python:3.12-slim

# Устанавливаем рабочую дирректорию
WORKDIR /app

# Копируем файл с зависимостями
COPY requirements.txt /app/

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем основной скрипт
COPY main.py /app/

# Устанавливаем переменные окружения (опционально)
ENV TELEGRAM_API_ID=""
ENV TELEGRAM_API_HASH=""
ENV TELEGRAM_CHAT_ID=""
ENV TELEGRAM_ALERT_CHAT_ID=""
ENV MESSAGE_THRESHOLD="50"

# запускаем приложение
CMD ["python", "main.py"]