"""Tests for database/db.py (sqlite3 layer)."""

import pytest

from database import db


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test_memory.db"
    db.init_db(path)
    return path


def test_init_db_creates_tables(db_path):
    with db._connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert "explicit_memory" in tables
    assert "relation_memory" in tables


def test_add_and_get_explicit_memory(db_path):
    memory_id = db.add_explicit_memory(
        user_id="u1",
        memory_type="event",
        content="Went to the park",
        entities=["park", "Sunday"],
        emotion_tag="joy",
        db_path=db_path,
    )
    memories = db.get_all_memories("u1", db_path=db_path)
    assert len(memories) == 1
    assert memories[0]["id"] == memory_id
    assert memories[0]["content"] == "Went to the park"
    assert memories[0]["entities"] == ["park", "Sunday"]
    assert memories[0]["emotion_tag"] == "joy"
    assert memories[0]["is_active"] is True


def test_soft_and_hard_delete_memory(db_path):
    memory_id = db.add_explicit_memory(
        user_id="u1",
        memory_type="fact",
        content="temp",
        db_path=db_path,
    )
    assert db.delete_memory(memory_id, hard=False, db_path=db_path) is True
    all_memories = db.get_all_memories("u1", db_path=db_path)
    assert all_memories[0]["is_active"] is False

    active = db.get_all_memories("u1", active_only=True, db_path=db_path)
    assert active == []

    assert db.delete_memory(memory_id, hard=True, db_path=db_path) is True
    assert db.get_all_memories("u1", db_path=db_path) == []


def test_add_relation_and_get_by_emotion(db_path):
    rel_id = db.add_relation_memory(
        user_id="u1",
        source_entity="Alice",
        target_entity="Bob",
        relation_type="friend",
        emotion_context="joy",
        db_path=db_path,
    )
    relations = db.get_relations_by_emotion("u1", "joy", db_path=db_path)
    assert len(relations) == 1
    assert relations[0]["id"] == rel_id
    assert relations[0]["source_entity"] == "Alice"

    empty = db.get_relations_by_emotion("u1", "anger", db_path=db_path)
    assert empty == []


def test_get_relation_by_id(db_path):
    rel_id = db.add_relation_memory(
        user_id="u1",
        source_entity="X",
        target_entity="Y",
        relation_type="knows",
        db_path=db_path,
    )
    rel = db.get_relation_by_id(rel_id, db_path=db_path)
    assert rel is not None
    assert rel["target_entity"] == "Y"
    assert db.get_relation_by_id(9999, db_path=db_path) is None


def test_update_relation(db_path):
    rel_id = db.add_relation_memory(
        user_id="u1",
        source_entity="A",
        target_entity="B",
        relation_type="likes",
        strength=1.0,
        db_path=db_path,
    )
    updated = db.update_relation(
        rel_id,
        strength=2.5,
        mention_count=3,
        db_path=db_path,
    )
    assert updated is not None
    assert updated["strength"] == 2.5
    assert updated["mention_count"] == 3
    assert updated["last_updated"] >= updated["first_seen"]


def test_update_relation_invalid_field(db_path):
    rel_id = db.add_relation_memory(
        user_id="u1",
        source_entity="A",
        target_entity="B",
        relation_type="likes",
        db_path=db_path,
    )
    with pytest.raises(ValueError, match="Cannot update fields"):
        db.update_relation(rel_id, user_id="hacker", db_path=db_path)


def test_update_relation_not_found(db_path):
    assert db.update_relation(404, strength=9.0, db_path=db_path) is None
