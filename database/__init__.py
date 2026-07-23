"""Database layer — Supabase backend."""

from database import db_supabase

__all__ = [
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

init_db = db_supabase.init_db
add_explicit_memory = db_supabase.add_explicit_memory
add_relation_memory = db_supabase.add_relation_memory
get_relations_by_emotion = db_supabase.get_relations_by_emotion
update_relation = db_supabase.update_relation
delete_memory = db_supabase.delete_memory
get_all_memories = db_supabase.get_all_memories
get_relation_by_id = db_supabase.get_relation_by_id
add_chat_history = db_supabase.add_chat_history
get_all_chat_history = db_supabase.get_all_chat_history
get_chat_history_by_user = db_supabase.get_chat_history_by_user