"""Database layer — sqlite3 CRUD and chat history support."""

from database import db
from database.manager import MemoryManager
from database.models import Base, MemoryRecord, RelationRecord

__all__ = [
    "db",
    "Base",
    "MemoryRecord",
    "RelationRecord",
    "MemoryManager",
    "init_db",
    "add_explicit_memory",
    "add_relation_memory",
    "get_relations_by_emotion",
    "update_relation",
    "delete_memory",
    "get_all_memories",
    "get_relation_by_id",
    "add_chat_history",
    "get_all_chat_history",
    "get_chat_history_by_user",
]

init_db = db.init_db
add_explicit_memory = db.add_explicit_memory
add_relation_memory = db.add_relation_memory
get_relations_by_emotion = db.get_relations_by_emotion
update_relation = db.update_relation
delete_memory = db.delete_memory
get_all_memories = db.get_all_memories
get_relation_by_id = db.get_relation_by_id

add_chat_history = db.add_chat_history
get_all_chat_history = db.get_all_chat_history
get_chat_history_by_user = db.get_chat_history_by_user