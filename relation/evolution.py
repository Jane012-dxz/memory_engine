"""Relation strength evolution over time."""

from database.manager import MemoryManager
from relation.extractor import RelationTriple


class RelationEvolver:
    """Merge new triples with existing relations and adjust strength."""

    REINFORCE_DELTA = 0.1
    DECAY_DELTA = -0.05
    MIN_STRENGTH = 0.0

    def __init__(self, db: MemoryManager | None = None) -> None:
        self.db = db or MemoryManager()

    def absorb(
        self,
        triples: list[RelationTriple],
        memory_id: int | None = None,
    ) -> list[int]:
        """Store or reinforce relations; returns list of relation IDs."""
        existing = self.db.list_relations(limit=1000)
        id_map: dict[tuple[str, str, str], int] = {
            (r.subject, r.predicate, r.obj): r.id for r in existing
        }
        result_ids: list[int] = []

        for triple in triples:
            key = (triple.subject, triple.predicate, triple.obj)
            if key in id_map:
                updated = self.db.update_relation_strength(
                    id_map[key], self.REINFORCE_DELTA
                )
                if updated:
                    result_ids.append(updated.id)
            else:
                record = self.db.add_relation(
                    subject=triple.subject,
                    predicate=triple.predicate,
                    obj=triple.obj,
                    memory_id=memory_id,
                    strength=1.0,
                )
                id_map[key] = record.id
                result_ids.append(record.id)

        return result_ids

    def decay_stale(self, threshold: float = 0.1) -> int:
        """Weaken all relations below threshold; remove those that hit zero."""
        count = 0
        for relation in self.db.list_relations(limit=10000):
            if relation.strength <= threshold:
                updated = self.db.update_relation_strength(
                    relation.id, self.DECAY_DELTA
                )
                if updated:
                    count += 1
        return count
