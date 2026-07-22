#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chroma-based vector store for semantic memory retrieval - 轻量版"""

from dataclasses import dataclass
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

from config import settings


@dataclass
class SearchResult:
    memory_id: str
    content: str
    distance: float
    metadata: dict


class MemoryVectorStore:
    """Persist and query memory embeddings with Chroma（轻量版，无需下载模型）"""

    COLLECTION_NAME = "memories"

    def __init__(self, persist_dir: Path | None = None):
        persist_dir = persist_dir or settings.chroma_persist_dir
        persist_dir.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=str(persist_dir))
        # 使用 Chroma 自带的轻量 embedding 函数（不需要额外下载模型）
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=embedding_functions.DefaultEmbeddingFunction(),
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, memory_id: int, content: str, metadata: dict | None = None) -> None:
        meta = metadata or {}
        meta.setdefault("memory_id", memory_id)
        self.collection.upsert(
            ids=[str(memory_id)],
            documents=[content],
            metadatas=[meta],
        )

    def search(self, query: str = None, query_text: str = None, top_k: int = 5) -> list[SearchResult]:
        # 兼容两种参数名
        search_query = query or query_text or ""
        if not search_query.strip():
            return []

        results = self.collection.query(
            query_texts=[search_query],
            n_results=top_k,
        )
        items: list[SearchResult] = []
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        dists = results.get("distances", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        for doc_id, doc, dist, meta in zip(ids, docs, dists, metas):
            items.append(
                SearchResult(
                    memory_id=doc_id,
                    content=doc or "",
                    distance=float(dist),
                    metadata=meta or {},
                )
            )
        return items

    def delete(self, memory_id: int) -> None:
        self.collection.delete(ids=[str(memory_id)])

    def count(self) -> int:
        return self.collection.count()