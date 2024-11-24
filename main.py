import os
import time
from telethon import TelegramClient, events
from prometheus_client import Counter, start_http_server

# Параметры конфигурации
API_ID = int(os.getenv("TELEGRAM_API_ID", ""))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")  # ID чата для мониторинга
ALERT_CHAT_ID = os.getenv("TELEGRAM_ALERT_CHAT_ID", "")  # ID чата для предупреждений
MESSAGE_THRESHOLD = int(os.getenv("MESSAGE_THRESHOLD", "50"))  # Максимум сообщений в час
MONITOR_INTERVAL = 3600  # Интервал мониторинга (1 час)

# Telegram клиент
client = TelegramClient('session_name', API_ID, API_HASH)

# Метрики для Prometheus
message_counter = Counter('telegram_message_total', 'Total number of message processed', ['chat_id'])
alerts_counter = Counter('telegram_alerts_total', 'Total number of alerts sent')

# Хранение статистики сообщений
message_counter = 0

async def send_alert():
    """Отправить предупреждение в Telegram."""
    await client.send_message(ALERT_CHAT_ID, f"Внимание, количество сообщений за час превысило {MESSAGE_THRESHOLD}!")
    alerts_counter.inc()  # Увеличиваем счетчик предупреждений

@client.on(events.NewMessage(chats=CHAT_ID))
async def count_messages(event):
    """Обработка новых сообщений."""
    global message_counter
    message_counter += 1
    message_counter.labels(chat_id=CHAT_ID).inc()  # Увеличиваем счетчик сообщений

async def monitor():
    """Мониторинг сообщенийю"""
    global message_counter
    while True:
        await client.loop.run_in_executor(None, time.sleep, MONITOR_INTERVAL)
        if message_counter > MESSAGE_THRESHOLD:
            await send_alert()
        message_counter = 0

if __name__ == "__main__":
    # Запускаем HTTP-сервер для экспорта метрик Prometheus
    start_http_server(8000)  # Метрики будут доступны на порту 8000
    with client:
        client.loop.create_task(monitor())
        client.run_until_disconnected()