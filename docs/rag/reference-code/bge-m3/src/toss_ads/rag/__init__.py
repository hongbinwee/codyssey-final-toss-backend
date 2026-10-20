"""Source-grounded Product Reviews RAG service."""

from .chunker import EMBEDDING_MODEL, build_product_chunks, build_review_chunks
from .types import EvidenceChunk, IndexSummary

__all__ = [
    "EMBEDDING_MODEL",
    "EvidenceChunk",
    "IndexSummary",
    "build_product_chunks",
    "build_review_chunks",
]
