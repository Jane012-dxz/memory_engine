"""Tests for synthetic data generation."""

from data.generator import SyntheticDataGenerator


def test_generate_memory():
    gen = SyntheticDataGenerator(locale="en_US")
    sample = gen.generate_memory()
    assert sample.content
    assert sample.emotion
    assert 0.0 <= sample.emotion_score <= 1.0


def test_generate_batch():
    gen = SyntheticDataGenerator(locale="en_US")
    batch = gen.generate_batch(count=5)
    assert len(batch) == 5


import pytest


@pytest.mark.slow
def test_seed_database(db, vector_store):
    gen = SyntheticDataGenerator(locale="en_US")
    count = gen.seed_database(count=3, db=db, vector_store=vector_store, with_relations=True)
    assert count == 3
    assert len(db.list_memories()) == 3
    assert vector_store.count() == 3
