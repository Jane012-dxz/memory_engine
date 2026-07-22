"""Shared pytest fixtures."""

import tempfile
from pathlib import Path

import pytest

from config import Settings
from database.manager import MemoryManager
from retrieval.store import MemoryVectorStore


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def temp_chroma_dir(tmp_path: Path) -> Path:
    return tmp_path / "chroma"


@pytest.fixture
def db(temp_db_path: Path) -> MemoryManager:
    return MemoryManager(db_path=temp_db_path)


@pytest.fixture
def vector_store(temp_chroma_dir: Path) -> MemoryVectorStore:
    return MemoryVectorStore(persist_dir=temp_chroma_dir, embedding_model="all-MiniLM-L6-v2")


@pytest.fixture
def test_settings(temp_db_path: Path, temp_chroma_dir: Path) -> Settings:
    return Settings(
        DEEPSEEK_API_KEY="test-key",
        DATABASE_PATH=temp_db_path,
        CHROMA_PERSIST_DIR=temp_chroma_dir,
    )
