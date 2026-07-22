"""Tests for retrieval module."""

import pytest


@pytest.mark.slow
def test_add_and_search(vector_store):
    vector_store.add(1, "I love programming in Python")
    vector_store.add(2, "The weather is sunny today")
    assert vector_store.count() == 2

    results = vector_store.search("coding language", top_k=1)
    assert len(results) >= 1
    assert results[0].memory_id == "1"


def test_search_empty_query(vector_store):
    assert vector_store.search("") == []


@pytest.mark.slow
def test_delete(vector_store):
    vector_store.add(99, "temporary memory")
    assert vector_store.count() == 1
    vector_store.delete(99)
    assert vector_store.count() == 0
