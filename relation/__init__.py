"""Relation extraction module."""

# from relation.evolution import RelationEvolver  # 暂时注释，evolution 依赖 manager，当前未使用
from relation.extractor import RelationExtractor, RelationTriple

__all__ = ["RelationExtractor", "RelationTriple"]  # 移除 RelationEvolver