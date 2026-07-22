"""Tests for chat module."""

from chat.generator import ChatGenerator, ChatMessage
from retrieval.store import SearchResult


def test_build_context_with_memories():
    chat = ChatGenerator(api_key="test")
    memories = [
        SearchResult(memory_id="1", content="User likes coffee", distance=0.1, metadata={}),
    ]
    context = chat.build_context(memories, relations=["Alice —knows→ Bob"])
    assert "coffee" in context
    assert "Alice" in context


def test_build_context_empty():
    chat = ChatGenerator(api_key="test")
    assert chat.build_context([]) == ""


def test_chat_message_dataclass():
    msg = ChatMessage(role="user", content="Hi")
    assert msg.role == "user"
