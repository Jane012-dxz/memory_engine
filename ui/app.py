"""Streamlit frontend for Memory Engine."""

import streamlit as st

from chat.generator import ChatGenerator, ChatMessage
from config import settings
from database.manager import MemoryManager
from emotion.recognizer import EmotionRecognizer
from relation.evolution import RelationEvolver
from relation.extractor import RelationExtractor
from retrieval.store import MemoryVectorStore


def _init_state() -> None:
    if "history" not in st.session_state:
        st.session_state.history: list[ChatMessage] = []
    if "db" not in st.session_state:
        settings.ensure_dirs()
        st.session_state.db = MemoryManager()
        st.session_state.vector_store = MemoryVectorStore()
        st.session_state.emotion = EmotionRecognizer()
        st.session_state.relation_extractor = RelationExtractor()
        st.session_state.relation_evolver = RelationEvolver(st.session_state.db)
        st.session_state.chat = ChatGenerator()


def _save_memory(content: str) -> None:
    db: MemoryManager = st.session_state.db
    vector_store: MemoryVectorStore = st.session_state.vector_store
    emotion: EmotionRecognizer = st.session_state.emotion
    extractor: RelationExtractor = st.session_state.relation_extractor
    evolver: RelationEvolver = st.session_state.relation_evolver

    emo = emotion.recognize(content)
    record = db.add_memory(
        content=content,
        emotion=emo.label,
        emotion_score=emo.score,
    )
    vector_store.add(
        record.id,
        content,
        metadata={"emotion": emo.label, "score": emo.score},
    )
    triples = extractor.extract(content)
    evolver.absorb(triples, memory_id=record.id)


def main() -> None:
    st.set_page_config(page_title="Memory Engine", page_icon="🧠", layout="wide")
    _init_state()

    st.title("🧠 Memory Engine")
    st.caption("Emotion-aware memory with relation extraction and vector retrieval")

    tab_chat, tab_memories, tab_relations = st.tabs(["Chat", "Memories", "Relations"])

    with tab_chat:
        for msg in st.session_state.history:
            with st.chat_message(msg.role):
                st.write(msg.content)

        if prompt := st.chat_input("Say something..."):
            st.session_state.history.append(ChatMessage(role="user", content=prompt))
            with st.chat_message("user"):
                st.write(prompt)

            _save_memory(prompt)

            vector_store: MemoryVectorStore = st.session_state.vector_store
            db: MemoryManager = st.session_state.db
            chat: ChatGenerator = st.session_state.chat

            hits = vector_store.search(prompt, top_k=5)
            relations = [
                f"{r.subject} —{r.predicate}→ {r.obj}"
                for r in db.list_relations(limit=20)
            ]
            context = chat.build_context(hits, relations)
            reply = chat.generate(prompt, history=st.session_state.history[:-1], memory_context=context)

            st.session_state.history.append(ChatMessage(role="assistant", content=reply))
            with st.chat_message("assistant"):
                st.write(reply)

    with tab_memories:
        db: MemoryManager = st.session_state.db
        for mem in db.list_memories(limit=50):
            st.markdown(f"**#{mem.id}** [{mem.emotion} {mem.emotion_score:.2f}] {mem.content}")

    with tab_relations:
        db: MemoryManager = st.session_state.db
        for rel in db.list_relations(limit=50):
            st.markdown(
                f"**#{rel.id}** (strength={rel.strength:.2f}) "
                f"{rel.subject} —{rel.predicate}→ {rel.obj}"
            )


if __name__ == "__main__":
    main()
