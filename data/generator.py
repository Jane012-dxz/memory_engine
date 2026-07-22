"""Generate synthetic memories and relations for testing and demos."""

import random
from dataclasses import dataclass

from faker import Faker

from database.manager import MemoryManager
from relation.evolution import RelationEvolver
from relation.extractor import RelationTriple
from retrieval.store import MemoryVectorStore


@dataclass
class SyntheticSample:
    content: str
    emotion: str
    emotion_score: float


EMOTIONS = ("joy", "sadness", "anger", "fear", "surprise", "neutral")

TEMPLATES = [
    "I feel {emotion} because {event}.",
    "Today {person} told me about {topic}, which made me {emotion}.",
    "I remember when we went to {place} and felt very {emotion}.",
    "{person} and I discussed {topic} yesterday.",
]


class SyntheticDataGenerator:
    """Produce fake memory entries and optional relation triples."""

    def __init__(self, locale: str = "zh_CN") -> None:
        self.fake = Faker(locale)

    def generate_memory(self) -> SyntheticSample:
        emotion = random.choice(EMOTIONS)
        person = self.fake.name()
        topic = self.fake.word()
        place = self.fake.city()
        event = self.fake.sentence(nb_words=6)
        template = random.choice(TEMPLATES)
        content = template.format(
            emotion=emotion,
            person=person,
            topic=topic,
            place=place,
            event=event,
        )
        score = round(random.uniform(0.3, 0.95), 2)
        return SyntheticSample(content=content, emotion=emotion, emotion_score=score)

    def generate_batch(self, count: int = 10) -> list[SyntheticSample]:
        return [self.generate_memory() for _ in range(count)]

    def seed_database(
        self,
        count: int = 20,
        db: MemoryManager | None = None,
        vector_store: MemoryVectorStore | None = None,
        with_relations: bool = True,
    ) -> int:
        """Insert synthetic samples into DB and vector store."""
        db = db or MemoryManager()
        vector_store = vector_store or MemoryVectorStore()
        evolver = RelationEvolver(db)
        created = 0

        for sample in self.generate_batch(count):
            record = db.add_memory(
                content=sample.content,
                emotion=sample.emotion,
                emotion_score=sample.emotion_score,
                source="synthetic",
            )
            vector_store.add(
                record.id,
                sample.content,
                metadata={"emotion": sample.emotion, "source": "synthetic"},
            )
            if with_relations:
                triples = self._fake_relations(sample.content)
                evolver.absorb(triples, memory_id=record.id)
            created += 1

        return created

    def _fake_relations(self, content: str) -> list[RelationTriple]:
        words = [w for w in content.replace(".", "").split() if len(w) > 2]
        if len(words) < 3:
            return []
        i = random.randint(0, len(words) - 3)
        return [
            RelationTriple(
                subject=words[i],
                predicate="related_to",
                obj=words[i + 2],
            )
        ]
