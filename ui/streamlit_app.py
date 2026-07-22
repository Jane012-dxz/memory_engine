#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用户共治界面 - Streamlit 应用"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import uuid
import pandas as pd
from datetime import datetime

from database.db import (
    get_all_memories,
    delete_memory,
    update_relation,
    get_relations_by_emotion,
    get_all_chat_history,
)
from chat.generator import generate_response
from database.db import init_db

# 页面配置
st.set_page_config(
    page_title="长程关系记忆引擎 - 情绪陪伴助手",
    page_icon="🧡",
    layout="wide"
)

# ========== 强制初始化数据库（部署时自动创建表） ==========
init_db()

# 初始化 session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())[:8]


# ============ 侧边栏：记忆管理 ============
with st.sidebar:
    st.title("📖 记忆管理")
    st.caption("查看和管理系统记住的关系")

    # 标签页
    tab1, tab2, tab3 = st.tabs(["📝 显式记忆", "🔗 关系记忆", "⚙️ 管理"])

    with tab1:
        st.caption("系统记住的用户信息、事件和偏好")

        memories = get_all_memories(
            user_id=st.session_state.user_id,
            active_only=True
        )

        if memories:
            df = pd.DataFrame(memories)
            display_cols = ["id", "memory_type", "content", "emotion_tag", "created_at"]
            if all(col in df.columns for col in display_cols):
                st.dataframe(
                    df[display_cols],
                    use_container_width=True,
                    column_config={
                        "id": "ID",
                        "memory_type": "类型",
                        "content": "内容",
                        "emotion_tag": "情绪",
                        "created_at": "创建时间",
                    }
                )

            delete_id = st.number_input(
                "输入记忆 ID 删除",
                min_value=0,
                step=1,
                key="delete_explicit"
            )
            if st.button("删除该记忆", key="btn_delete_explicit"):
                if delete_id > 0:
                    result = delete_memory(delete_id, hard=False)
                    if result:
                        st.success(f"✅ 记忆 {delete_id} 已删除")
                        st.rerun()
                    else:
                        st.error("删除失败，请检查 ID 是否正确")
        else:
            st.info("暂无显式记忆")

    with tab2:
        st.caption("系统构建的关系图谱（实体之间的因果、触发等关系）")

        if st.button("🔄 刷新记忆"):
            st.rerun()

        relations = get_relations_by_emotion(
            user_id=st.session_state.user_id,
            emotion=None,
            status='active'
        )

        if relations:
            df_rel = pd.DataFrame(relations)
            display_cols = ["id", "source_entity", "target_entity", "relation_type", "strength", "emotion_context"]
            if all(col in df_rel.columns for col in display_cols):
                st.dataframe(
                    df_rel[display_cols],
                    use_container_width=True,
                    column_config={
                        "id": "ID",
                        "source_entity": "源实体",
                        "target_entity": "目标实体",
                        "relation_type": "关系类型",
                        "strength": "强度",
                        "emotion_context": "情绪上下文",
                    }
                )

            freeze_id = st.number_input(
                "输入关系 ID 冻结",
                min_value=0,
                step=1,
                key="freeze_rel"
            )
            if st.button("冻结该关系", key="btn_freeze"):
                if freeze_id > 0:
                    result = update_relation(freeze_id, status="frozen")
                    if result:
                        st.success(f"✅ 关系 {freeze_id} 已冻结")
                        st.rerun()
                    else:
                        st.error("冻结失败")
        else:
            st.info("暂无关系记忆")

    with tab3:
        st.subheader("⚙️ 批量操作")

        st.write(f"👤 当前用户ID: {st.session_state.user_id}")

        # 按主题删除（同时删除显式记忆和关系记忆）
        topic = st.text_input("输入主题词批量遗忘（如：论文）")
        if st.button("🗑️ 删除该主题所有记忆", type="secondary"):
            if topic:
                from database.db import _connect, _get_db_path
                db_path = _get_db_path("storage/memory.db")
                deleted_count = 0
                
                with _connect(db_path) as conn:
                    # 1. 删除关系记忆（relation_memory）中包含主题词的记录
                    cursor_rel = conn.execute(
                        "DELETE FROM relation_memory WHERE user_id = ? AND (source_entity LIKE ? OR target_entity LIKE ?)",
                        (st.session_state.user_id, f"%{topic}%", f"%{topic}%")
                    )
                    deleted_count += cursor_rel.rowcount
                    
                    # 2. 删除显式记忆（explicit_memory）中包含主题词的记录
                    cursor_exp = conn.execute(
                        "DELETE FROM explicit_memory WHERE user_id = ? AND content LIKE ?",
                        (st.session_state.user_id, f"%{topic}%")
                    )
                    deleted_count += cursor_exp.rowcount
                    
                    conn.commit()
                
                if deleted_count > 0:
                    st.success(f"✅ 已删除 {deleted_count} 条包含「{topic}」的记忆")
                    st.rerun()
                else:
                    st.warning(f"⚠️ 未找到包含「{topic}」的记忆")

        st.divider()

        # 统计信息
        st.caption("📊 统计信息")
        total_memories = len(get_all_memories(st.session_state.user_id, active_only=True))
        total_relations = len(get_relations_by_emotion(st.session_state.user_id, emotion=None, status='active'))
        st.metric("显式记忆总数", total_memories)
        st.metric("关系记忆总数", total_relations)

        st.divider()
        st.subheader("📈 运营数据汇总")

        # 密码验证
        admin_password = st.text_input("请输入管理员密码查看运营数据", type="password", key="admin_pwd")
        if admin_password == "admin123":
            if st.button("📊 刷新汇总数据"):
                from database.db import _connect, _get_db_path
                db_path = _get_db_path("storage/memory.db")
                with _connect(db_path) as conn:
                    user_count = conn.execute(
                        "SELECT COUNT(DISTINCT user_id) FROM relation_memory"
                    ).fetchone()[0]
                    total_relations_all = conn.execute(
                        "SELECT COUNT(*) FROM relation_memory"
                    ).fetchone()[0]
                    recent_inputs = conn.execute(
                        "SELECT user_id, source_entity, target_entity, emotion_context, evidence, last_updated "
                        "FROM relation_memory ORDER BY last_updated DESC LIMIT 10"
                    ).fetchall()

                st.metric("👥 总用户数", user_count)
                st.metric("📝 总关系记录数", total_relations_all)

                if recent_inputs:
                    st.caption("📋 最近10条关系记录")
                    for row in recent_inputs:
                        st.text(
                            f"[{row['user_id'][:8]}] {row['source_entity']} → {row['target_entity']} "
                            f"(情绪: {row['emotion_context']})"
                        )
                        if row['evidence']:
                            st.caption(f"   💬 用户说: {row['evidence']}")
                else:
                    st.info("暂无关系记录")
        elif admin_password:
            st.error("❌ 密码错误，请重试")
        else:
            st.info("🔒 请输入管理员密码查看运营数据汇总")

        st.divider()
        st.subheader("📋 用户聊天记录")

        if st.button("📋 查看所有用户聊天记录"):
            history = get_all_chat_history(limit=200)
            if history:
                st.caption(f"共 {len(history)} 条记录（最多显示200条）")
                for record in history:
                    role_icon = "🧑" if record['role'] == 'user' else "🤖"
                    st.text(f"{role_icon} [{record['user_id'][:8]}] {record['role']}: {record['content']}")
                    st.caption(f"  情绪: {record.get('emotion', '')} | {record.get('created_at', '')}")
                    st.divider()
            else:
                st.info("暂无聊天记录")

        st.divider()
        st.subheader("📥 数据导出")

        if st.button("📥 导出数据库文件"):
            db_path = "storage/memory.db"
            try:
                with open(db_path, "rb") as f:
                    db_bytes = f.read()
                st.download_button(
                    label="⬇️ 点击下载 memory.db",
                    data=db_bytes,
                    file_name="memory.db",
                    mime="application/octet-stream"
                )
            except FileNotFoundError:
                st.error("❌ 数据库文件不存在，请先产生一些数据")


# ============ 主体：对话区 ============
st.title("💬 对话")
st.caption("基于关系演化的情绪陪伴智能体")

# 显示历史消息
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    else:
        st.chat_message("assistant").write(msg["content"])

# 输入框
user_input = st.chat_input("说说你的心事...")

if user_input:
    # 添加用户消息
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 生成回应
    with st.spinner("正在思考..."):
        response = generate_response(
            user_input=user_input,
            user_id=st.session_state.user_id
        )

    # 添加 AI 消息
    st.session_state.messages.append({"role": "assistant", "content": response})

    # 重绘
    st.rerun()