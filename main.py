import os
import time
from telethon import TelegramClient, events
from prometheus_client import Counter, start_http_server

# Параметры конфигурации
API_ID = int(os.getenv("TELEGRAM_API_ID", ""))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", ""))  # ID чата для мониторинга
ALERT_CHAT_ID = int(os.getenv("TELEGRAM_ALERT_CHAT_ID", ""))  # ID чата для предупреждений
MESSAGE_THRESHOLD = int(os.getenv("MESSAGE_THRESHOLD", "5"))  # Максимум сообщений в час
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MONITOR_INTERVAL = 15  # Интервал мониторинга (1 час)

# Telegram клиент
# client = TelegramClient('session_name', API_ID, API_HASH)
client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Метрики для Prometheus
message_counter = Counter('telegram_message_total', 'Total number of message processed', ['chat_id'])
alerts_counter = Counter('telegram_alerts_total', 'Total number of alerts sent')

# Хранение статистики сообщений
message_counter_int = 0

async def send_alert():
    """Отправить предупреждение в Telegram."""
    await client.send_message(ALERT_CHAT_ID, f"Внимание, количество сообщений за час превысило {MESSAGE_THRESHOLD}!")
    alerts_counter.inc()  # Увеличиваем счетчик предупреждений

@client.on(events.NewMessage(chats=CHAT_ID))
async def count_messages(event):
    """Обработка новых сообщений."""
    global message_counter, message_counter_int
    message_counter_int += 1
    message_counter.labels(chat_id=CHAT_ID).inc()  # Увеличиваем счетчик сообщений

async def monitor():
    """Мониторинг сообщений."""
    global message_counter_int
    while True:
        await client.loop.run_in_executor(None, time.sleep, MONITOR_INTERVAL)
        if message_counter_int > MESSAGE_THRESHOLD:
            await send_alert()
        message_counter_int = 0

if __name__ == "__main__":
    # Запускаем HTTP-сервер для экспорта метрик Prometheus
    start_http_server(8000)  # Метрики будут доступны на порту 8000
    with client:
        client.loop.create_task(monitor())
        client.run_until_disconnected()