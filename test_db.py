#!/usr/bin/env python3
"""Manual test script for database/db.py — run: python test_db.py"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from database.db import (
    add_explicit_memory,
    add_relation_memory,
    delete_memory,
    get_all_memories,
    get_relation_by_id,
    get_relations_by_emotion,
    init_db,
    update_relation,
)

# Use a separate DB file so demo runs don't affect production data
DEMO_DB = Path("./storage/test_demo.db")
USER_ID = "test_user"


def pprint(title: str, data: object) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)
    if isinstance(data, list):
        if not data:
            print("  (empty)")
        for i, item in enumerate(data, 1):
            print(f"  [{i}] {json.dumps(item, ensure_ascii=False, indent=2)}")
    elif isinstance(data, dict):
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"  {data}")


def main() -> None:
    # 清理旧的演示数据库，保证每次运行结果一致
    if DEMO_DB.exists():
        DEMO_DB.unlink()
        print(f"  已清理旧数据库: {DEMO_DB.resolve()}")

    # 1. 初始化数据库
    print("\n>>> Step 1: 初始化数据库")
    init_db(DEMO_DB)
    print(f"  数据库已初始化: {DEMO_DB.resolve()}")

    # 2. 添加 explicit_memory
    print("\n>>> Step 2: 添加 explicit_memory")
    memory_id = add_explicit_memory(
        user_id=USER_ID,
        memory_type="event",
        content="论文被拒",
        entities=["论文"],
        emotion_tag="沮丧",
        db_path=DEMO_DB,
    )
    print(f"  插入成功, memory_id = {memory_id}")

    # 3. 添加 relation_memory
    print("\n>>> Step 3: 添加 relation_memory")
    relation_id = add_relation_memory(
        user_id=USER_ID,
        source_entity="论文压力",
        target_entity="入睡困难",
        relation_type="causes",
        strength=0.6,
        emotion_context="焦虑",
        db_path=DEMO_DB,
    )
    print(f"  插入成功, relation_id = {relation_id}")

    # 4. 查询所有记忆
    print("\n>>> Step 4: 查询所有记忆")
    memories = get_all_memories(USER_ID, db_path=DEMO_DB)
    pprint(f"用户 {USER_ID} 的全部记忆 (共 {len(memories)} 条)", memories)

    # 5. 按情绪查询关系
    print("\n>>> Step 5: 按情绪查询关系 (emotion_context='焦虑')")
    relations = get_relations_by_emotion(USER_ID, "焦虑", db_path=DEMO_DB)
    pprint(f"情绪为「焦虑」的关系 (共 {len(relations)} 条)", relations)

    # 6. 更新关系 strength
    print("\n>>> Step 6: 更新关系 strength → 0.9")
    before = get_relation_by_id(relation_id, db_path=DEMO_DB)
    print(f"  更新前 strength = {before['strength'] if before else 'N/A'}")
    updated = update_relation(relation_id, strength=0.9, db_path=DEMO_DB)
    pprint("更新后的关系", updated)

    # 7. 删除一条记忆
    print("\n>>> Step 7: 删除记忆 (soft delete, hard=False)")
    deleted = delete_memory(memory_id, hard=False, db_path=DEMO_DB)
    print(f"  delete_memory({memory_id}) → {deleted}")

    # 8. 再次查询，确认删除生效
    print("\n>>> Step 8: 再次查询所有记忆，确认删除生效")
    all_memories = get_all_memories(USER_ID, db_path=DEMO_DB)
    active_memories = get_all_memories(USER_ID, active_only=True, db_path=DEMO_DB)
    pprint(f"全部记忆 (含已软删, 共 {len(all_memories)} 条)", all_memories)
    pprint(f"仅有效记忆 (active_only=True, 共 {len(active_memories)} 条)", active_memories)

    if all_memories and not all_memories[0]["is_active"]:
        print("\n  [OK] 删除生效: 记忆仍在库中，但 is_active = False (软删除)")
    elif not all_memories:
        print("\n  [OK] 删除生效: 记忆已从库中移除 (硬删除)")
    else:
        print("\n  [FAIL] 删除可能未生效，请检查")

    print(f"\n{'=' * 60}")
    print("  全部测试步骤执行完毕")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
