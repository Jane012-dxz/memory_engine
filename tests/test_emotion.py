"""Tests for emotion module."""

from emotion.recognizer import EmotionRecognizer, EmotionResult


def test_emotion_result_defaults():
    result = EmotionResult(label="neutral", score=0.0)
    assert result.label == "neutral"
    assert result.score == 0.0


def test_parse_valid_json():
    recognizer = EmotionRecognizer(api_key="test")
    raw = '{"label": "joy", "score": 0.85}'
    result = recognizer._parse_response(raw)
    assert result.label == "joy"
    assert result.score == 0.85


def test_parse_invalid_json_fallback():
    recognizer = EmotionRecognizer(api_key="test")
    result = recognizer._parse_response("not json")
    assert result.label == "neutral"


def test_empty_text_returns_neutral():
    recognizer = EmotionRecognizer(api_key="test")
    result = recognizer.recognize("   ")
    assert result.label == "neutral"
    assert result.score == 0.0
