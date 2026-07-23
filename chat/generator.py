#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对话生成模块：整合所有模块，调用大模型 API 生成回应"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import re
from typing import Optional, List
import requests

from config import settings
from emotion.detector import detect_emotion
from relation.extractor import extract_relations
from relation.updater import update_or_create_relation, check_and_resolve_conflict
from database.db_supabase import add_explicit_memory, get_all_memories, add_chat_history


# ============ 主接口 ============

def generate_response(
    user_input: str,
    user_id: str = "default_user",
    db_path: Optional[str] = None
) -> str:
    """
    生成情绪陪伴回应（整合所有模块）
    """
    print(f"[DEBUG] generate_response 收到的 user_id: {user_id}")

    # 1. 识别情绪
    emotion = detect_emotion(user_input)

    # 2. 抽取关系
    relations = extract_relations(user_input)

    # ========== 显式记忆写入 ==========
    explicit_patterns = [
        (r'(?:我叫|我是|我的名字是)\s*([^\s，,。.!！？?]+)', 'fact', '名字'),
        (r'(?:我今年|我)\s*(\d+)\s*(?:岁|岁了)', 'fact', '年龄'),
        (r'我喜欢\s*([^，,。.!！？?]+)', 'preference', '喜欢'),
        (r'我讨厌\s*([^，,。.!！？?]+)', 'preference', '讨厌'),
        (r'我(?:是|是一名|是一位)\s*([^，,。.!！？?]+)', 'fact', '身份'),
    ]
    
    for pattern, mem_type, label in explicit_patterns:
        match = re.search(pattern, user_input)
        if match:
            content = f"{label}: {match.group(1).strip()}"
            add_explicit_memory(
                user_id=user_id,
                memory_type=mem_type,
                content=content,
                entities=[match.group(1).strip()],
                emotion_tag=emotion,
                db_path=db_path
            )
            break

    # 3. 写入/更新关系
    for rel in relations:
        if rel.get('source') and rel.get('target'):
            check_and_resolve_conflict(
                user_id=user_id,
                source=rel['source'],
                target=rel['target'],
                new_relation_type=rel['relation_type'],
                emotion_context=emotion,
                evidence=user_input,
                db_path=db_path
            )
            update_or_create_relation(
                user_id=user_id,
                source=rel['source'],
                target=rel['target'],
                relation_type=rel['relation_type'],
                emotion_context=emotion,
                evidence=user_input,
                db_path=db_path
            )

    # 4. 记录用户输入到聊天历史
    add_chat_history(user_id, 'user', user_input, emotion, db_path=db_path)

    # 5. 检索显式记忆
    explicit_memories = get_all_memories(user_id, active_only=True, db_path=db_path)
    
    explicit_text = ""
    name = None
    if explicit_memories:
        explicit_text = "【用户画像】:\n"
        for mem in explicit_memories[:5]:
            content = mem.get('content', '')
            explicit_text += f"- {content}\n"
            if content.startswith('名字:'):
                name = content.replace('名字:', '').strip()
    
    name_instruction = ""
    if name:
        name_instruction = f"用户的名字是 {name}，请在回应中称呼用户为 {name}。"
    else:
        name_instruction = "用户没有告诉你名字，不要主动给用户起名字。"

    # 6. 构造历史关系上下文
    historical = []
    for rel in relations:
        if rel.get('source') and rel.get('target'):
            historical.append({
                'source_entity': rel['source'],
                'target_entity': rel['target'],
                'strength': 0.6,
                'content': f"{rel['source']} → {rel['target']} ({rel['relation_type']})",
                'id': 0
            })

    # 7. 构造提示词
    relation_text = ""
    for rel in relations:
        if rel.get('source') and rel.get('target'):
            relation_text += f"- {rel['source']} → {rel['target']} ({rel['relation_type']})\n"

    historical_text = ""
    for h in historical:
        historical_text += f"- {h.get('source_entity', '')} → {h.get('target_entity', '')} (强度: {h.get('strength', 0)})\n"

    # 判断是否是求助模式（用户明确要建议/方法）
    help_keywords = ['怎么办', '怎么', '如何', '给建议', '建议', '帮我', '帮我一下', '具体方法', '有什么办法', '怎么做', '怎么解决']
    is_help_request = any(kw in user_input for kw in help_keywords)

    # ========== 检测危机信号 ==========
    crisis_keywords = ['自杀', '自伤', '轻生', '不想活了', '活着没意思', '想死', '结束生命', '不想活']
    is_crisis = any(kw in user_input for kw in crisis_keywords)

    if is_crisis:
        # 危机模式：最高优先级，不执行任何其他逻辑
        return _crisis_response(user_input, user_id, emotion, db_path)

    if is_help_request:
        help_instruction = """【重要】用户正在明确求助，要求具体建议。请在简短共情后，直接给出 2-3 条具体可操作的建议。
不要再问“是什么让你焦虑”“你现在的感受是怎样的”这类问题。"""
    else:
        help_instruction = """用户是在倾诉情绪，没有明确求助。请先共情一句，再温和追问一句（最多追问一次），不要连续追问。"""

    prompt = f"""你是一个温暖的情绪陪伴助手。请基于以下信息回应用户：

{name_instruction}

【用户画像】:
{explicit_text or "暂无"}

【当前情绪】: {emotion}

【用户当前表达的关系】:
{relation_text or "无"}

【历史相关关系】:
{historical_text or "无"}

【回应要求】:
1. 先表达理解和承接（一句话即可，不超过一句）。
2. {help_instruction}
3. 给建议时用“你可以试试……”“有没有考虑过……”等句式，不要用“你应该”“你必须”。
4. 不要使用任何诊断性语言（如“抑郁”“焦虑症”“障碍”等）。
5. 用温暖、自然的语气回应。

用户说: "{user_input}"

请生成回应："""

    # 8. 调用大模型 API
    try:
        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        headers = {
            "Authorization": "Bearer bd027701718f4404876494c89f6d0bba.kQOej6ydUiYMvI3R",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "glm-4-flash",
            "messages": [
                {"role": "system", "content": "你是一个温暖、共情的情绪陪伴助手。永远不要使用诊断性语言。如果用户明确求助，请直接给具体建议。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 600
        }

        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        # 9. 记录AI回复到聊天历史
        add_chat_history(user_id, 'assistant', reply, emotion, db_path=db_path)

        return reply

    except Exception as e:
        print(f"[API] 调用失败: {e}")
        fallback = _fallback_response(emotion, user_input)
        # 降级回复也要记录
        add_chat_history(user_id, 'assistant', fallback, emotion, db_path=db_path)
        return fallback


def _crisis_response(user_input: str, user_id: str, emotion: str, db_path: Optional[str] = None) -> str:
    """危机信号专用回应：不调用 API，直接返回安全引导"""
    reply = """我听到了你的痛苦，这一定非常难熬。请你不要一个人扛着。

**请立即拨打全国心理援助热线：12356**，有人会倾听你、帮助你。

如果你愿意，也请告诉身边信任的人，或者去最近的医院心理科/精神科。

你不是一个人，请一定要联系专业人士寻求帮助。"""
    
    # 记录危机回应到聊天历史
    add_chat_history(user_id, 'assistant', reply, emotion, db_path=db_path)
    return reply


def _fallback_response(emotion: str, user_input: str) -> str:
    """当 API 不可用时的降级回应"""
    responses = {
        '焦虑': "听起来你最近有些焦虑。愿意多和我聊聊让你担心的事情吗？",
        '疲惫': "你听起来很疲惫，辛苦了。如果愿意的话，可以和我说说。",
        '委屈': "感觉到你有些委屈，我在这里听着。",
        '愤怒': "听起来这件事让你很生气，愿意具体说说发生了什么吗？",
        '开心': "听起来你现在心情不错，真好！愿意分享一下让你开心的事情吗？",
        '平静': "嗯，我明白了。有什么想聊的，我都在。",
    }
    return responses.get(emotion, "我听到了。你想继续说吗？")