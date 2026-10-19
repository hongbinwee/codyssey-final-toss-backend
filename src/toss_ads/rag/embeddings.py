"""LangChain FastEmbed adapter and tokenizer helpers."""

from __future__ import annotations

from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

from .config import Settings

EMBEDDING_DIMENSION = 384
MODEL_MAX_TOKENS = 128


def create_embedder(settings: Settings) -> FastEmbedEmbeddings:
    embedder = FastEmbedEmbeddings(
        model_name=settings.embedding_model,
        max_length=MODEL_MAX_TOKENS,
        cache_dir=settings.fastembed_cache_path,
        batch_size=settings.embedding_batch_size,
    )
    if embedder.model.embedding_size != EMBEDDING_DIMENSION:
        raise ValueError("embedding_dimension_mismatch")
    return embedder


def count_tokens(embedder: FastEmbedEmbeddings, text: str) -> int:
    """Count with the exact tokenizer loaded by the embedding adapter."""
    return int(embedder.model.token_count(text))
