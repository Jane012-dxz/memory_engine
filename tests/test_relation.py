"""Tests for relation module."""

from relation.evolution import RelationEvolver
from relation.extractor import RelationExtractor, RelationTriple


def test_parse_relations():
    extractor = RelationExtractor(api_key="test")
    raw = '{"relations": [{"subject": "Alice", "predicate": "likes", "object": "Bob"}]}'
    triples = extractor._parse_response(raw)
    assert len(triples) == 1
    assert triples[0].subject == "Alice"
    assert triples[0].obj == "Bob"


def test_absorb_new_relations(db):
    evolver = RelationEvolver(db)
    triples = [RelationTriple("X", "knows", "Y")]
    ids = evolver.absorb(triples, memory_id=1)
    assert len(ids) == 1
    relations = db.list_relations()
    assert relations[0].strength == 1.0


def test_absorb_reinforces_existing(db):
    evolver = RelationEvolver(db)
    triple = RelationTriple("X", "knows", "Y")
    evolver.absorb([triple])
    evolver.absorb([triple])
    relations = db.list_relations()
    assert len(relations) == 1
    assert relations[0].strength == 1.1
