"""SQLite database layer using sqlite3."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import settings

ALLOWED_RELATION_FIELDS = frozenset({
    "source_entity",
    "target_entity",
    "relation_type",
    "strength",
    "emotion_context",
    "status",
    "mention_count",
    "evidence",
})


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _get_db_path(db_path: str | Path | None = None) -> Path:
    """获取数据库路径，统一转为 Path 对象"""
    if db_path is None:
        db_path = settings.database_path
    if isinstance(db_path, str):
        db_path = Path(db_path)
    db_path = db_path.resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(_get_db_path(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    if "entities" in data and data["entities"] is not None:
        try:
            data["entities"] = json.loads(data["entities"])
        except (json.JSONDecodeError, TypeError):
            pass
    if "is_active" in data:
        data["is_active"] = bool(data["is_active"])
    return data


def init_db(db_path: Path | None = None) -> None:
    """Create tables if they do not exist."""
    with _connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS explicit_memory (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT    NOT NULL,
                memory_type TEXT    NOT NULL,
                content     TEXT    NOT NULL,
                entities    TEXT,
                emotion_tag TEXT    DEFAULT '',
                created_at  TEXT    NOT NULL,
                expires_at  TEXT,
                is_active   INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS relation_memory (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         TEXT    NOT NULL,
                source_entity   TEXT    NOT NULL,
                target_entity   TEXT    NOT NULL,
                relation_type   TEXT    NOT NULL,
                strength        REAL    NOT NULL DEFAULT 1.0,
                emotion_context TEXT    DEFAULT '',
                status          TEXT    NOT NULL DEFAULT 'active',
                first_seen      TEXT    NOT NULL,
                last_updated    TEXT    NOT NULL,
                mention_count   INTEGER NOT NULL DEFAULT 1,
                evidence        TEXT    DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS chat_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT    NOT NULL,
                role        TEXT    NOT NULL,
                content     TEXT    NOT NULL,
                emotion     TEXT    DEFAULT '',
                created_at  TEXT    NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_explicit_memory_user
                ON explicit_memory (user_id, is_active);

            CREATE INDEX IF NOT EXISTS idx_relation_memory_user_emotion
                ON relation_memory (user_id, emotion_context, status);

            CREATE INDEX IF NOT EXISTS idx_chat_history_user
                ON chat_history (user_id, created_at);
            """
        )
        conn.commit()


def add_explicit_memory(
    user_id: str,
    memory_type: str,
    content: str,
    entities: list | dict | None = None,
    emotion_tag: str = "",
    expires_at: str | None = None,
    is_active: bool = True,
    db_path: Path | None = None,
) -> int:
    """Insert an explicit memory row and return its id."""
    init_db(db_path)
    entities_json = json.dumps(entities, ensure_ascii=False) if entities is not None else None
    created_at = _now_iso()

    with _connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO explicit_memory (
                user_id, memory_type, content, entities,
                emotion_tag, created_at, expires_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                memory_type,
                content,
                entities_json,
                emotion_tag,
                created_at,
                expires_at,
                int(is_active),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def add_relation_memory(
    user_id: str,
    source_entity: str,
    target_entity: str,
    relation_type: str,
    strength: float = 1.0,
    emotion_context: str = "",
    evidence: str = "",
    status: str = "active",
    db_path: Path | None = None,
) -> int:
    """Insert a relation memory row and return its id."""
    init_db(db_path)
    now = _now_iso()

    with _connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO relation_memory (
                user_id, source_entity, target_entity, relation_type,
                strength, emotion_context, status,
                first_seen, last_updated, mention_count, evidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                source_entity,
                target_entity,
                relation_type,
                strength,
                emotion_context,
                status,
                now,
                now,
                1,
                evidence,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def get_relations_by_emotion(
    user_id: str,
    emotion: str | None = None,
    status: str | None = "active",
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    init_db(db_path)
    with _connect(db_path) as conn:
        if emotion is None and status is None:
            rows = conn.execute(
                "SELECT * FROM relation_memory WHERE user_id = ? ORDER BY last_updated DESC",
                (user_id,),
            ).fetchall()
        elif emotion is None:
            rows = conn.execute(
                "SELECT * FROM relation_memory WHERE user_id = ? AND status = ? ORDER BY last_updated DESC",
                (user_id, status),
            ).fetchall()
        elif status is None:
            rows = conn.execute(
                "SELECT * FROM relation_memory WHERE user_id = ? AND emotion_context = ? ORDER BY last_updated DESC",
                (user_id, emotion),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM relation_memory WHERE user_id = ? AND emotion_context = ? AND status = ? ORDER BY last_updated DESC",
                (user_id, emotion, status),
            ).fetchall()
    return [_row_to_dict(row) for row in rows]  # type: ignore[misc]


def update_relation(
    relation_id: int,
    db_path: Path | None = None,
    **kwargs: Any,
) -> dict[str, Any] | None:
    """Update allowed fields on a relation; returns the updated row or None."""
    if not kwargs:
        return get_relation_by_id(relation_id, db_path=db_path)

    invalid = set(kwargs) - ALLOWED_RELATION_FIELDS
    if invalid:
        raise ValueError(f"Cannot update fields: {', '.join(sorted(invalid))}")

    init_db(db_path)
    fields = dict(kwargs)
    fields["last_updated"] = _now_iso()

    set_clause = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [relation_id]

    with _connect(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE relation_memory SET {set_clause} WHERE id = ?",
            values,
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None

    return get_relation_by_id(relation_id, db_path=db_path)


def delete_memory(
    memory_id: int,
    hard: bool = False,
    db_path: Path | None = None,
) -> bool:
    """Soft-delete (deactivate) or hard-delete an explicit memory."""
    init_db(db_path)
    with _connect(db_path) as conn:
        if hard:
            cursor = conn.execute(
                "DELETE FROM explicit_memory WHERE id = ?",
                (memory_id,),
            )
        else:
            cursor = conn.execute(
                "UPDATE explicit_memory SET is_active = 0 WHERE id = ?",
                (memory_id,),
            )
        conn.commit()
        return cursor.rowcount > 0


def get_all_memories(
    user_id: str,
    active_only: bool = False,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Return all explicit memories for a user, newest first."""
    init_db(db_path)
    query = """
        SELECT * FROM explicit_memory
        WHERE user_id = ?
    """
    params: list[Any] = [user_id]
    if active_only:
        query += " AND is_active = 1"
    query += " ORDER BY created_at DESC"

    with _connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]  # type: ignore[misc]


def get_relation_by_id(
    relation_id: int,
    db_path: Path | None = None,
) -> dict[str, Any] | None:
    """Return a single relation by id."""
    init_db(db_path)
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM relation_memory WHERE id = ?",
            (relation_id,),
        ).fetchone()
    return _row_to_dict(row)


# ============ 对话历史记录 ============

def add_chat_history(
    user_id: str,
    role: str,
    content: str,
    emotion: str = "",
    db_path: Path | None = None,
) -> int:
    """插入一条对话历史记录"""
    init_db(db_path)
    created_at = _now_iso()
    with _connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO chat_history (user_id, role, content, emotion, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, role, content, emotion, created_at),
        )
        conn.commit()
        return int(cursor.lastrowid)


def get_all_chat_history(
    limit: int = 200,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """获取所有用户的对话历史（管理员用）"""
    init_db(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, role, content, emotion, created_at
            FROM chat_history
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_chat_history_by_user(
    user_id: str,
    limit: int = 50,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """获取某个用户的对话历史"""
    init_db(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, role, content, emotion, created_at
            FROM chat_history
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]