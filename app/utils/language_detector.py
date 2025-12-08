import struct
from app.models.schemas import Language
import structlog 
import re

logger = structlog.get_logger()

class LanguageDetector:
    def __init__(self):
        self.urdu_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]')

        self.english_indicators = [
            'doctor', 'appointment', 'time', 'when', 'where', 'help', 'need', 'want', 'think', 'hello', 'hi', 'please'
        ]

        self.urdu_romanized_indicators = [
            'doctor', 'daktar', 'waqt', 'kahan', 'kahan', 'madad', 'chahiye', 'salam', 'assalam', 'shukria'
        ]

    def detect(self, text: str) -> Language:
        """
        Detect language from text
        Returns: Language.URDU or Language.ENGLISH
        """

        if not text or len(text.strip()) < 2:
            return Language.URDU

        text_lower = text.lower().strip()

        urdu_chars = len(self.urdu_pattern.findall(text))

        if urdu_chars > 0:
            logger.info("language_detected", language="urdu", method="script", urdu_chars=urdu_chars)
            return Language.URDU

        english_score = sum(1 for word in self.english_indicators if word in text_lower)

        words = text_lower.split()
        avg_word_length = sum(len(w) for w in words) / len(words) if words else 0

        if english_score > 0 or (avg_word_length < 6 and any(c.isacii() for c in text)):
            logger.info("language_detected", language="english", method="indicators", score=english_score)

        logger.info("language_detected", language="urdu", method="default")
        return Language.URDU
    
    def get_confidence(self, text: str) -> float:
        """
        Get confidence score for language detection (0.0 to 1.0)
        """

        if not text:
            return 0.0
        
        text_lower = text.lower().strip()
        urdu_chars = len(self.urdu_pattern.findall(text))
        total_chars = len(text.replace(' ', ''))

        if total_chars == 0:
            return 0.0

        if urdu_chars > 0:
            return min(1.0, urdu_chars / total_chars + 0.5)

        english_score = sum(1 for word in self.english_indicators if word in text_lower)
        words_count = len(text_lower.strip())

        if words_count == 0:
            return 0.0

        confidence = min(1.0, (english_score / words_count) * 2)
        return confidence if confidence > 0.3 else 0.5

language_detector = LanguageDetector()

        