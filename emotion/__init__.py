"""Emotion recognition module."""

from emotion.detector import detect_emotion, load_emotion_dict
from emotion.recognizer import EmotionRecognizer, EmotionResult

__all__ = [
    "EmotionRecognizer",
    "EmotionResult",
    "detect_emotion",
    "load_emotion_dict",
]
