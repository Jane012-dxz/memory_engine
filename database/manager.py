"""Database manager — connection, schema init, and CRUD."""

from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from config import settings
from database.models import Base, MemoryRecord, RelationRecord


class MemoryManager:
    """SQLite-backed memory and relation storage."""

    def __init__(self, db_path: Path | None = None) -> None:
        path = db_path or settings.database_path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{path}", echo=False)
        Base.metadata.create_all(self.engine)
        self._Session = sessionmaker(bind=self.engine)

    def session(self) -> Session:
        return self._Session()

    # --- Memory CRUD ---

    def add_memory(
        self,
        content: str,
        emotion: str = "neutral",
        emotion_score: float = 0.0,
        source: str = "user",
    ) -> MemoryRecord:
        with self.session() as session:
            record = MemoryRecord(
                content=content,
                emotion=emotion,
                emotion_score=emotion_score,
                source=source,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def get_memory(self, memory_id: int) -> MemoryRecord | None:
        with self.session() as session:
            return session.get(MemoryRecord, memory_id)

    def list_memories(self, limit: int = 50) -> list[MemoryRecord]:
        with self.session() as session:
            stmt = select(MemoryRecord).order_by(MemoryRecord.created_at.desc()).limit(limit)
            return list(session.scalars(stmt))

    def delete_memory(self, memory_id: int) -> bool:
        with self.session() as session:
            record = session.get(MemoryRecord, memory_id)
            if record is None:
                return False
            session.delete(record)
            session.commit()
            return True

    # --- Relation CRUD ---

    def add_relation(
        self,
        subject: str,
        predicate: str,
        obj: str,
        memory_id: int | None = None,
        strength: float = 1.0,
    ) -> RelationRecord:
        with self.session() as session:
            record = RelationRecord(
                subject=subject,
                predicate=predicate,
                obj=obj,
                memory_id=memory_id,
                strength=strength,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def list_relations(self, limit: int = 100) -> list[RelationRecord]:
        with self.session() as session:
            stmt = select(RelationRecord).order_by(RelationRecord.updated_at.desc()).limit(limit)
            return list(session.scalars(stmt))

    def update_relation_strength(self, relation_id: int, delta: float) -> RelationRecord | None:
        with self.session() as session:
            record = session.get(RelationRecord, relation_id)
            if record is None:
                return None
            record.strength = max(0.0, record.strength + delta)
            session.commit()
            session.refresh(record)
            return record
