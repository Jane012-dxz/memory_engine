#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""关系演化更新模块：写入/更新关系记忆"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_supabase import (
    add_relation_memory,
    get_relations_by_emotion,
    get_relation_by_id,
    update_relation,
)
from typing import Optional


def update_or_create_relation(
    user_id: str,
    source: str,
    target: str,
    relation_type: str,
    emotion_context: str,
    evidence: str = "",
    db_path: Optional[str] = None
) -> int:
    """
    更新或创建关系记忆

    Args:
        user_id: 用户标识
        source: 源实体
        target: 目标实体
        relation_type: 关系类型
        emotion_context: 当前情绪标签
        evidence: 用户原始输入
        db_path: 数据库路径

    Returns:
        int: 关系的 relation_id
    """
    if not source or not target:
        return -1

    # 查询是否已存在相同的关系
    existing = _find_existing_relation(user_id, source, target, relation_type, db_path)

    if existing:
        # 更新已有关系（不更新 evidence，保留首次证据）
        new_strength = min(1.0, existing.get('strength', 0.5) + 0.1)
        new_mention_count = existing.get('mention_count', 0) + 1

        update_relation(
            existing['id'],
            db_path=db_path,
            strength=new_strength,
            mention_count=new_mention_count,
            status='active'
        )
        return existing['id']
    else:
        # 创建新关系时传入 evidence
        return add_relation_memory(
            user_id=user_id,
            source_entity=source,
            target_entity=target,
            relation_type=relation_type,
            strength=0.6,
            emotion_context=emotion_context,
            evidence=evidence,
            db_path=db_path
        )


def _find_existing_relation(
    user_id: str,
    source: str,
    target: str,
    relation_type: str,
    db_path: Optional[str] = None
) -> Optional[dict]:
    """
    查找已存在的关系记录
    """
    all_relations = get_relations_by_emotion(
        user_id=user_id,
        emotion=None,  # 查询所有情绪
        status=None,   # 查询所有状态
        db_path=db_path
    )

    for rel in all_relations:
        if (rel.get('source_entity') == source and
            rel.get('target_entity') == target and
            rel.get('relation_type') == relation_type):
            return rel
    return None


def check_and_resolve_conflict(
    user_id: str,
    source: str,
    target: str,
    new_relation_type: str,
    emotion_context: str,
    evidence: str = "",
    db_path: Optional[str] = None
) -> str:
    """
    检查并解决关系冲突

    Args:
        user_id: 用户标识
        source: 源实体
        target: 目标实体
        new_relation_type: 新关系类型
        emotion_context: 当前情绪标签
        evidence: 用户原始输入
        db_path: 数据库路径

    Returns:
        str: "conflict_resolved" 或 "no_conflict"
    """
    if not source or not target:
        return "no_conflict"

    # 查询所有状态为 active 的关系
    all_relations = get_relations_by_emotion(
        user_id=user_id,
        emotion=None,
        status='active',
        db_path=db_path
    )

    # 定义对立关系对
    conflict_pairs = [
        ('causes', 'alleviates'),
        ('alleviates', 'causes'),
        ('triggers', 'alleviates'),
        ('alleviates', 'triggers'),
    ]

    for rel in all_relations:
        if (rel.get('source_entity') == source and
            rel.get('target_entity') == target):
            old_type = rel.get('relation_type')
            if (old_type, new_relation_type) in conflict_pairs:
                # 存在冲突，标记旧关系为被替代
                update_relation(
                    rel['id'],
                    db_path=db_path,
                    status='superseded'
                )
                # 创建新关系时传入 evidence
                add_relation_memory(
                    user_id=user_id,
                    source_entity=source,
                    target_entity=target,
                    relation_type=new_relation_type,
                    strength=0.6,
                    emotion_context=emotion_context,
                    evidence=evidence,
                    db_path=db_path
                )
                return "conflict_resolved"

    return "no_conflict"