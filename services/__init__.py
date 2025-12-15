"""
Services package for AgriAI Backend
Contains three main services:
- text_translation: Text translation between languages
- speech_translation: Speech-to-text transcription
- analysis: Sentiment analysis and Named Entity Recognition (NER)
"""

from .text_translation import (
    translate_text,
    translate_text_by_language_name,
    get_language_code,
    LANGUAGE_MAP,
    TranslationError
)
from .speech_translation import (
    transcribe_audio,
    get_stt_language_code,
    STT_LANGUAGE_MAP,
    TranscriptionError
)
from .analysis import (
    analyze_sentiment,
    analyze_entities
)

__all__ = [
    # Text translation
    "translate_text",
    "translate_text_by_language_name",
    "get_language_code",
    "LANGUAGE_MAP",
    "TranslationError",
    # Speech translation
    "transcribe_audio",
    "get_stt_language_code",
    "STT_LANGUAGE_MAP",
    "TranscriptionError",
    # Analysis
    "analyze_sentiment",
    "analyze_entities",
]

