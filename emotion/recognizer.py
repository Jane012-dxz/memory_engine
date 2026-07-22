"""Emotion recognition via DeepSeek LLM."""

import json
import re
from dataclasses import dataclass

from openai import OpenAI

from config import settings


@dataclass
class EmotionResult:
    label: str
    score: float
    raw: str = ""


EMOTION_LABELS = ("joy", "sadness", "anger", "fear", "surprise", "disgust", "neutral")


class EmotionRecognizer:
    """Detect emotion label and intensity from text."""

    SYSTEM_PROMPT = (
        "You are an emotion classifier. Given user text, respond with JSON only: "
        '{"label": "<one of joy|sadness|anger|fear|surprise|disgust|neutral>", '
        '"score": <float 0-1 indicating intensity>}'
    )

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.client = OpenAI(
            api_key=api_key or settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
        self.model = model or settings.deepseek_model

    def recognize(self, text: str) -> EmotionResult:
        if not text.strip():
            return EmotionResult(label="neutral", score=0.0)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0.0,
        )
        raw = response.choices[0].message.content or ""
        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> EmotionResult:
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
                label = str(data.get("label", "neutral")).lower()
                score = float(data.get("score", 0.5))
                if label not in EMOTION_LABELS:
                    label = "neutral"
                return EmotionResult(label=label, score=min(1.0, max(0.0, score)), raw=raw)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
        return EmotionResult(label="neutral", score=0.5, raw=raw)
