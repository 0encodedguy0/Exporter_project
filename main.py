import os
import time
from telethon import TelegramClient, events
from prometheus_client import Counter, start_http_server
from collections import defaultdict
import spacy
from datetime import datetime, timedelta

# Параметры конфигурации
API_ID = int(os.getenv("TELEGRAM_API_ID", ""))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", ""))  # ID чата для мониторинга
ALERT_CHAT_ID = int(os.getenv("TELEGRAM_ALERT_CHAT_ID", ""))  # ID чата для предупреждений
MESSAGE_THRESHOLD = int(os.getenv("MESSAGE_THRESHOLD", "5"))  # Максимум сообщений в час
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MONITOR_INTERVAL = 15  # Интервал мониторинга (1 час)

# Telegram клиент
client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Метрики для Prometheus
message_counter = Counter('telegram_message_total', 'Total number of message processed', ['chat_id'])
alerts_counter = Counter('telegram_alerts_total', 'Total number of alerts sent')

# Хранение статистики сообщений
message_counter_int = 0
ner_counts = defaultdict(int) 
ner_time_window = timedelta(seconds=MONITOR_INTERVAL)
last_reset_time = datetime.now()

nlp = spacy.load("ru_core_news_sm")

async def send_alert():
    """Отправить предупреждение в Telegram."""
    await client.send_message(ALERT_CHAT_ID, f"Внимание, количество сообщений за час превысило {MESSAGE_THRESHOLD}!")
    alerts_counter.inc()  # Увеличиваем счетчик предупреждений

async def send_ner_summary():
    """Send NER summary to the alert chat."""
    summary = f"Сводка по именованным сущностям за последние {MONITOR_INTERVAL} секунд:\n"
    for entity, count in sorted(ner_counts.items(), key=lambda x: x[1], reverse=True):
        summary += f"{entity}: {count}\n"
    
    await client.send_message(ALERT_CHAT_ID, summary)

def extract_named_entities(text):
    """Extract named entities from the given text and update the NER counter."""
    doc = nlp(text)
    for ent in doc.ents:
        ner_counts[ent.text] += 1

    # uncomment for logging. TODO: move to proper logging module
    # print(text)
    # print(doc)
    # print(ner_counts)

@client.on(events.NewMessage(chats=CHAT_ID))
async def count_messages(event):
    """Обработка новых сообщений."""
    global message_counter, message_counter_int, ner_counts
    message_counter_int += 1
    message_counter.labels(chat_id=CHAT_ID).inc()  # Увеличиваем счетчик сообщений

    message_text = event.message.message
    if message_text:
        extract_named_entities(message_text)

async def monitor():
    """Мониторинг сообщений."""
    global message_counter_int, ner_counts, last_reset_time
    while True:
        await client.loop.run_in_executor(None, time.sleep, MONITOR_INTERVAL)
        if message_counter_int > MESSAGE_THRESHOLD:
            await send_alert()
        message_counter_int = 0

        if datetime.now() - last_reset_time >= ner_time_window:
            await send_ner_summary()
            # ner_counts.clear() # uncomment if you want to reset ner_counts
            last_reset_time = datetime.now()

if __name__ == "__main__":
    # Запускаем HTTP-сервер для экспорта метрик Prometheus
    start_http_server(8000)  # Метрики будут доступны на порту 8000
    with client:
        client.loop.create_task(monitor())
        client.run_until_disconnected()