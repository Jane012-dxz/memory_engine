"""Supabase database layer for memory_engine."""

import streamlit as st
from supabase import create_client, Client
from datetime import datetime
from typing import Any, Optional


def get_conn() -> Client:
    """获取 Supabase 客户端"""
    if "supabase" not in st.session_state:
        url = st.secrets["connections"]["supabase"]["url"]
        key = st.secrets["connections"]["supabase"]["key"]
        print(f"[DEBUG] Supabase URL: {url}")
        print(f"[DEBUG] Supabase Key: {key[:20]}...")
        st.session_state.supabase = create_client(url, key)
    return st.session_state.supabase


def _now_iso() -> str:
    return datetime.now().isoformat()


# ============ 初始化 ============

def init_db() -> None:
    """初始化（Supabase 无需建表，表已在 SQL 中创建）"""
    pass


# ============ 显式记忆 ============

def add_explicit_memory(
    user_id: str,
    memory_type: str,
    content: str,
    entities: list | dict | None = None,
    emotion_tag: str = "",
    expires_at: str | None = None,
    is_active: bool = True,
    db_path=None,
) -> int:
    """插入显式记忆"""
    import json
    try:
        conn = get_conn()
        data = {
            "user_id": user_id,
            "memory_type": memory_type,
            "content": content,
            "entities": json.dumps(entities, ensure_ascii=False) if entities else None,
            "emotion_tag": emotion_tag,
            "expires_at": expires_at,
            "is_active": is_active
        }
        print(f"[DEBUG] 插入显式记忆: {data}")
        result = conn.table("explicit_memory").insert(data).execute()
        print(f"[DEBUG] 插入成功: {result.data}")
        return result.data[0]["id"] if result.data else -1
    except Exception as e:
        print(f"[ERROR] Supabase 插入显式记忆失败: {e}")
        raise


def get_all_memories(
    user_id: str,
    active_only: bool = False,
    db_path=None,
) -> list[dict[str, Any]]:
    """获取用户的显式记忆"""
    try:
        conn = get_conn()
        query = conn.table("explicit_memory").select("*").eq("user_id", user_id)
        if active_only:
            query = query.eq("is_active", True)
        query = query.order("created_at", desc=True)
        result = query.execute()
        print(f"[DEBUG] 查询显式记忆成功: {len(result.data)} 条")
        return result.data
    except Exception as e:
        print(f"[ERROR] Supabase 查询显式记忆失败: {e}")
        return []


def delete_memory(
    memory_id: int,
    hard: bool = False,
    db_path=None,
) -> bool:
    """删除显式记忆"""
    try:
        conn = get_conn()
        if hard:
            result = conn.table("explicit_memory").delete().eq("id", memory_id).execute()
        else:
            result = conn.table("explicit_memory").update({"is_active": False}).eq("id", memory_id).execute()
        return len(result.data) > 0
    except Exception as e:
        print(f"[ERROR] Supabase 删除显式记忆失败: {e}")
        return False


# ============ 关系记忆 ============

def add_relation_memory(
    user_id: str,
    source_entity: str,
    target_entity: str,
    relation_type: str,
    strength: float = 1.0,
    emotion_context: str = "",
    evidence: str = "",
    status: str = "active",
    db_path=None,
) -> int:
    """插入关系记忆"""
    try:
        conn = get_conn()
        now = _now_iso()
        data = {
            "user_id": user_id,
            "source_entity": source_entity,
            "target_entity": target_entity,
            "relation_type": relation_type,
            "strength": strength,
            "emotion_context": emotion_context,
            "evidence": evidence,
            "status": status,
            "first_seen": now,
            "last_updated": now,
            "mention_count": 1
        }
        print(f"[DEBUG] 插入关系记忆: {data}")
        result = conn.table("relation_memory").insert(data).execute()
        print(f"[DEBUG] 插入成功: {result.data}")
        return result.data[0]["id"] if result.data else -1
    except Exception as e:
        print(f"[ERROR] Supabase 插入关系记忆失败: {e}")
        raise


def get_relations_by_emotion(
    user_id: str = "",
    emotion: str | None = None,
    status: str | None = "active",
    db_path=None,
) -> list[dict[str, Any]]:
    """按情绪和状态查询关系记忆"""
    try:
        conn = get_conn()
        # 直接查询所有记录（不筛选 user_id）
        query = conn.table("relation_memory").select("*")
        
        # 如果指定了 user_id 才筛选
        if user_id:
            query = query.eq("user_id", user_id)
        if emotion is not None:
            query = query.eq("emotion_context", emotion)
        if status is not None:
            query = query.eq("status", status)
        query = query.order("last_updated", desc=True)
        result = query.execute()
        print(f"[DEBUG] 查询到 {len(result.data)} 条关系记录")
        return result.data
    except Exception as e:
        print(f"[ERROR] Supabase 查询关系记忆失败: {e}")
        return []


def get_relation_by_id(
    relation_id: int,
    db_path=None,
) -> dict[str, Any] | None:
    """根据 ID 获取关系"""
    try:
        conn = get_conn()
        result = conn.table("relation_memory").select("*").eq("id", relation_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"[ERROR] Supabase 查询关系失败: {e}")
        return None


def update_relation(
    relation_id: int,
    db_path=None,
    **kwargs,
) -> dict[str, Any] | None:
    """更新关系"""
    try:
        conn = get_conn()
        kwargs["last_updated"] = _now_iso()
        result = conn.table("relation_memory").update(kwargs).eq("id", relation_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"[ERROR] Supabase 更新关系失败: {e}")
        return None


# ============ 聊天历史 ============

def add_chat_history(
    user_id: str,
    role: str,
    content: str,
    emotion: str = "",
    db_path=None,
) -> int:
    """插入聊天记录"""
    try:
        conn = get_conn()
        data = {
            "user_id": user_id,
            "role": role,
            "content": content,
            "emotion": emotion
        }
        print(f"[DEBUG] 插入聊天记录: {data}")
        result = conn.table("chat_history").insert(data).execute()
        print(f"[DEBUG] 插入成功: {result.data}")
        return result.data[0]["id"] if result.data else -1
    except Exception as e:
        print(f"[ERROR] Supabase 插入聊天记录失败: {e}")
        print(f"[ERROR] 错误详情: {e.args if hasattr(e, 'args') else '无'}")
        raise


def get_all_chat_history(
    limit: int = 200,
    db_path=None,
) -> list[dict[str, Any]]:
    """获取所有用户的聊天历史"""
    try:
        conn = get_conn()
        result = conn.table("chat_history").select("*").order("created_at", desc=True).limit(limit).execute()
        print(f"[DEBUG] 查询聊天历史成功: {len(result.data)} 条")
        return result.data
    except Exception as e:
        print(f"[ERROR] Supabase 查询聊天历史失败: {e}")
        return []


def get_chat_history_by_user(
    user_id: str,
    limit: int = 50,
    db_path=None,
) -> list[dict[str, Any]]:
    """获取单个用户的聊天历史"""
    try:
        conn = get_conn()
        result = conn.table("chat_history").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
        print(f"[DEBUG] 查询用户聊天历史成功: {len(result.data)} 条")
        return result.data
    except Exception as e:
        print(f"[ERROR] Supabase 查询用户聊天历史失败: {e}")
        return []