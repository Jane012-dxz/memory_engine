"""Tests for database module."""

from database.models import MemoryRecord, RelationRecord


def test_add_and_get_memory(db):
    record = db.add_memory("Hello world", emotion="joy", emotion_score=0.8)
    assert record.id is not None
    fetched = db.get_memory(record.id)
    assert fetched is not None
    assert fetched.content == "Hello world"
    assert fetched.emotion == "joy"


def test_list_memories(db):
    db.add_memory("First")
    db.add_memory("Second")
    memories = db.list_memories(limit=10)
    assert len(memories) == 2


def test_delete_memory(db):
    record = db.add_memory("To delete")
    assert db.delete_memory(record.id) is True
    assert db.get_memory(record.id) is None


def test_add_relation(db):
    rel = db.add_relation("Alice", "knows", "Bob", strength=1.0)
    assert isinstance(rel, RelationRecord)
    relations = db.list_relations()
    assert len(relations) == 1
    assert relations[0].subject == "Alice"


def test_update_relation_strength(db):
    rel = db.add_relation("A", "likes", "B")
    updated = db.update_relation_strength(rel.id, 0.5)
    assert updated is not None
    assert updated.strength == 1.5
