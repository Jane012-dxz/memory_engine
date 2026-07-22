"""Rule-based emotion detection using jieba and keyword dictionary."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import jieba

_DICT_PATH = Path(__file__).parent / "emotion_dict.json"
_DEFAULT_EMOTION = "平静"

_emotion_dict: dict[str, list[str]] | None = None
_keyword_to_emotion: dict[str, str] | None = None


def load_emotion_dict(path: Path | None = None) -> dict[str, list[str]]:
    """Load emotion keyword dictionary from JSON file."""
    global _emotion_dict, _keyword_to_emotion

    dict_path = path or _DICT_PATH
    with dict_path.open(encoding="utf-8") as f:
        data: dict[str, list[str]] = json.load(f)

    _emotion_dict = data
    _keyword_to_emotion = {}
    for emotion, keywords in data.items():
        for kw in keywords:
            _keyword_to_emotion[kw] = emotion
            jieba.add_word(kw)

    return data


def _ensure_loaded() -> tuple[dict[str, list[str]], dict[str, str]]:
    if _emotion_dict is None or _keyword_to_emotion is None:
        load_emotion_dict()
    assert _emotion_dict is not None and _keyword_to_emotion is not None
    return _emotion_dict, _keyword_to_emotion


def detect_emotion(text: str) -> str:
    """
    Detect the dominant emotion label in text.

    Tokenizes with jieba, counts keyword hits per emotion category,
    and returns the label with the most hits. Returns "平静" if none match.
    """
    if not text or not text.strip():
        return _DEFAULT_EMOTION

    emotion_dict, keyword_to_emotion = _ensure_loaded()
    counts: Counter[str] = Counter({emotion: 0 for emotion in emotion_dict})

    tokens = jieba.lcut(text.strip())
    for token in tokens:
        if not token.strip():
            continue

        emotion = keyword_to_emotion.get(token)
        if emotion is not None:
            counts[emotion] += 1
            continue

        # jieba 可能产出「太委屈」等包含关键词的 token，做子串补充匹配
        for kw, emo in keyword_to_emotion.items():
            if len(kw) >= 2 and kw in token:
                counts[emo] += 1
                break

    if not counts or max(counts.values()) == 0:
        return _DEFAULT_EMOTION

    return max(counts, key=lambda e: counts[e])


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    load_emotion_dict()

    test_sentences = [
        "论文被拒了，我担心毕不了业，最近总是睡不着",
        "今天加班到很晚，筋疲力尽，一点精神都没有",
        "明明是我做的，功劳却是别人的，太委屈了",
        "这个bug改了一整天还报错，真的受不了，火大",
        "今天天气不错，心情还行，没事",
        "明天有个会议要准备材料",
    ]

    print("=" * 50)
    print("  Emotion Detector 测试")
    print("=" * 50)
    for sentence in test_sentences:
        label = detect_emotion(sentence)
        print(f"\n文本: {sentence}")
        print(f"情绪: {label}")
    print("\n" + "=" * 50)
