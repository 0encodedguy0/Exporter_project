import spacy
from transformers import pipeline
from prometheus_client import Counter, Gauge
from collections import defaultdict
from datetime import datetime, timedelta


MONITOR_INTERVAL = 15
MESSAGE_THRESHOLD = 5
TOP_K_ENTITIES = 6

class Metrics:
    def __init__(self, client, chat_id, alert_chat_id=None):
        self.client = client

        self.total_messages = 0
        self.ner_counts = defaultdict(int)
        self.ner_time_window = timedelta(seconds=MONITOR_INTERVAL)
        self.last_reset_time = datetime.now()

        self.message_counter = Counter('telegram_message_total', 'Total number of message processed', ['chat_id'])
        self.alerts_counter = Counter('telegram_alerts_total', 'Total number of alerts sent')
        self.entities_gauge = Gauge('entities', 'frequencies', ['entity'])
        self.emotion_gauge = Gauge('emotion_score', 'Detected emotion from messages', ['emotion'])
        self.sentiment_gauge = Gauge('sentiment_score', 'Detected sentiment from messages', ['sentiment'])

        self.emotion_pipeline = pipeline("text-classification", model="seara/rubert-tiny2-russian-emotion-detection-ru-go-emotions")
        self.sentiment_pipeline = pipeline("sentiment-analysis", model="seara/rubert-tiny2-russian-sentiment")

        self.chat_id = chat_id
        if alert_chat_id is None:
            self.alert_chat_id = self.chat_id
        else:
            self.alert_chat_id = alert_chat_id

        self.nlp = spacy.load("ru_core_news_sm")

    def analyze_emotion(self, text):
        """Analyze emotion of the given text and return detected emotions."""
        results = self.emotion_pipeline(text)
        return results[0]['label'], results[0]['score']  # Return emotion label and confidence score

    def analyze_sentiment(self, text):
        """Analyze sentiment of the given text (positive, neutral, negative)."""
        results = self.sentiment_pipeline(text)
        return results[0]['label'], results[0]['score']  # Return sentiment label and confidence score

    def update_metrics(self):
        """Update Prometheus metrics based on the current entity frequencies."""
        self.entities_gauge.clear()
        for entity, count in self.ner_counts.items():
            self.entities_gauge.labels(entity=entity).set(count)

    def extract_named_entities(self, text):
        """Extract named entities from the given text and update the NER counter."""
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.text not in self.ner_counts.keys():
                self.ner_counts[ent.text] = 1
            else:
                self.ner_counts[ent.text] += 1

        self.ner_counts = dict(sorted(self.ner_counts.items(), key=lambda item: item[1])[:TOP_K_ENTITIES])
        self.update_metrics()

    async def send_ner_summary(self):
        """Send NER summary to the alert chat."""
        summary = f"Сводка по именованным сущностям за последние {MONITOR_INTERVAL} секунд:\n"
        for entity, count in sorted(self.ner_counts.items(), key=lambda x: x[1], reverse=True):
            summary += f"{entity}: {count}\n"
        
        await self.client.send_message(self.alert_chat_id, summary)

    async def send_alert(self):
        """Отправить предупреждение в Telegram."""
        await self.client.send_message(self.alert_chat_id, f"Внимание, количество сообщений за час превысило {MESSAGE_THRESHOLD}!")
        self.alerts_counter.inc()  # Увеличиваем счетчик предупреждений

    async def count_messages(self, event):
        """Process new messages."""    
        self.total_messages += 1
        self.message_counter.labels(chat_id=self.chat_id).inc()  # Increment message counter

        message_text = event.message.message
        if message_text:
            # Анализ сущностей
            self.extract_named_entities(message_text)

            # Анализ эмоций
            emotion_label, emotion_score = self.analyze_emotion(message_text)
            self.emotion_gauge.labels(emotion=emotion_label).set(emotion_score)

            # Анализ тональности
            sentiment_label, sentiment_score = self.analyze_sentiment(message_text)
            self.sentiment_gauge.labels(sentiment=sentiment_label).set(sentiment_score)
