# Используем образ python 3.12
FROM python:3.12-slim

# Устанавливаем рабочую дирректорию
WORKDIR /app

# Копируем файл с зависимостями
COPY requirements.txt /app/

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    && apt-get clean

# Устанавливаем зависимости
RUN pip install setuptools -U
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -U spacy
RUN python -m spacy download ru_core_news_sm
RUN pip install tensorflow
RUN pip install tf-keras

# Копируем основной скрипт
COPY main.py /app/
COPY utils.py /app/
COPY prometheus.yml /app/
COPY grafana/ /app/

# Устанавливаем переменные окружения (опционально)
ENV TELEGRAM_API_ID: ""
ENV TELEGRAM_API_HASH: ""
ENV TELEGRAM_CHAT_ID: ""
ENV TELEGRAM_ALERT_CHAT_ID: ""
ENV BOT_TOKEN=""
ENV MESSAGE_THRESHOLD="5"

# запускаем приложение
CMD ["python", "main.py"]
