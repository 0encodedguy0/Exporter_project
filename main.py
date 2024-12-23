import os
import time
from telethon import TelegramClient, events
from prometheus_client import start_http_server
from datetime import datetime

from utils import Metrics, MESSAGE_THRESHOLD, MONITOR_INTERVAL

# Параметры конфигурации
API_ID = int(os.getenv("TELEGRAM_API_ID", ""))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", ""))  # ID чата для мониторинга
ALERT_CHAT_ID = int(os.getenv("TELEGRAM_ALERT_CHAT_ID", ""))  # ID чата для предупреждений
BOT_TOKEN = os.getenv("BOT_TOKEN", "") # токен бота

# Telegram клиент
client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
metrics = Metrics(client=client, chat_id=CHAT_ID, alert_chat_id=ALERT_CHAT_ID)

client.add_event_handler(metrics.count_messages, events.NewMessage(chats=CHAT_ID))

async def monitor(metrics):
    """Мониторинг сообщений."""
    last_reset_time = datetime.now()
    # global message_counter_int, ner_counts, last_reset_time
    while True:
        await client.loop.run_in_executor(None, time.sleep, MONITOR_INTERVAL)

        if metrics.total_messages > MESSAGE_THRESHOLD:
            await metrics.send_alert()
        metrics.total_messages = 0

        if datetime.now() - last_reset_time >= metrics.ner_time_window:
            await metrics.send_ner_summary()
            # ner_counts.clear() # uncomment if you want to reset ner_counts
            last_reset_time = datetime.now()

if __name__ == "__main__":
    # Запускаем HTTP-сервер для экспорта метрик Prometheus
    start_http_server(8000)  # Метрики будут доступны на порту 8000
    with client:
        client.loop.create_task(monitor(metrics))
        client.run_until_disconnected()