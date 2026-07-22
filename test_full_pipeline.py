#!/usr/bin/env python3
"""测试完整链路"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from emotion.detector import detect_emotion
from relation.extractor import extract_relations
from relation.updater import update_or_create_relation
from chat.generator import generate_response

USER_ID = "test_user"

def test_full_pipeline():
    print("=" * 60)
    print("🧪 测试完整链路")
    print("=" * 60)

    user_input = "论文压力让我睡不着，最近特别焦虑"
    print(f"\n📝 用户输入: {user_input}")

    # 1. 情绪识别
    emotion = detect_emotion(user_input)
    print(f"   ✅ 情绪识别: {emotion}")

    # 2. 关系抽取
    relations = extract_relations(user_input)
    print(f"   ✅ 关系抽取: {relations}")

    # 3. 写入关系
    for rel in relations:
        if rel.get('source') and rel.get('target'):
            rel_id = update_or_create_relation(
                user_id=USER_ID,
                source=rel['source'],
                target=rel['target'],
                relation_type=rel['relation_type'],
                emotion_context=emotion,
                db_path="storage/memory.db"  # 明确指定
            )
            print(f"   ✅ 关系写入: {rel['source']} → {rel['target']} (id={rel_id})")

    # 4. 生成回应
    print("\n🤖 生成回应:")
    response = generate_response(user_input, user_id=USER_ID, db_path="storage/memory.db")
    print(f"   {response}")

    print("\n" + "=" * 60)
    print("✅ 测试完成")

if __name__ == "__main__":
    test_full_pipeline()