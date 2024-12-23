import spacy
from transformers import pipeline
from prometheus_client import Counter, Gauge
from collections import defaultdict
from datetime import datetime, timedelta
from gensim.corpora.dictionary import Dictionary
from gensim.models.ldamodel import LdaModel
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import string
import nltk

nltk.download('punkt')
nltk.download('stopwords')

MONITOR_INTERVAL = 15
MESSAGE_THRESHOLD = 5
TOP_K_ENTITIES = 6
NUM_TOPICS = 5  # Количество тем для LDA

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
        self.topic_gauge = Gauge('topic_score', 'Detected topics from messages', ['topic'])

        self.emotion_pipeline = pipeline("text-classification", model="seara/rubert-tiny2-russian-emotion-detection-ru-go-emotions")
        self.sentiment_pipeline = pipeline("sentiment-analysis", model="blanchefort/rubert-base-cased-sentiment")

        self.chat_id = chat_id
        if alert_chat_id is None:
            self.alert_chat_id = self.chat_id
        else:
            self.alert_chat_id = alert_chat_id

        self.nlp = spacy.load("ru_core_news_sm")

        # Для Topic Modelling
        self.stop_words = set(stopwords.words("russian"))
        self.dictionary = None
        self.lda_model = None

    def analyze_emotion(self, text):
        """Analyze emotion of the given text and return detected emotions."""
        results = self.emotion_pipeline(text)
        return results[0]['label'], results[0]['score']  # Return emotion label and confidence score

    def analyze_sentiment(self, text):
        """Analyze sentiment of the given text (positive, neutral, negative)."""
        results = self.sentiment_pipeline(text)
        return results[0]['label'], results[0]['score']  # Return sentiment label and confidence score

    def preprocess_texts(self, texts):
        """Preprocess a list of texts for LDA."""
        processed_texts = []
        for text in texts:
            tokens = word_tokenize(text.lower())
            tokens = [t for t in tokens if t not in self.stop_words and t not in string.punctuation]
            processed_texts.append(tokens)
        return processed_texts

    def train_lda_model(self, texts):
        """Train an LDA model on the given texts."""
        processed_texts = self.preprocess_texts(texts)
        self.dictionary = Dictionary(processed_texts)
        corpus = [self.dictionary.doc2bow(text) for text in processed_texts]
        self.lda_model = LdaModel(corpus, num_topics=NUM_TOPICS, id2word=self.dictionary, passes=10)

    def get_topics(self, text):
        """Infer topics from a single text."""
        if not self.lda_model or not self.dictionary:
            return []

        tokens = [t for t in word_tokenize(text.lower()) if t not in self.stop_words and t not in string.punctuation]
        bow = self.dictionary.doc2bow(tokens)
        topics = self.lda_model.get_document_topics(bow)
        return topics

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
            self.extract_named_entities(message_text)  # Extract named entities

            # Анализ эмоций
            emotion_label, confidence_score = self.analyze_emotion(message_text)
            self.emotion_gauge.labels(emotion=emotion_label).set(confidence_score)

            # Анализ тональности
            sentiment_label, sentiment_score = self.analyze_sentiment(message_text)

            # Вывод тем
            topics = self.get_topics(message_text)
            if topics:
                for topic_id, topic_score in topics:
                    self.topic_gauge.labels(topic=self.lda_model.print_topic(topic_id)).set(topic_score)
