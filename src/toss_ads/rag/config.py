"""Environment-backed runtime configuration with no secret-bearing repr."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass


DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def _positive_int(
    name: str, default: int, maximum: int | None = None, minimum: int = 1
) -> int:
    raw = os.getenv(name)
    try:
        value = default if raw is None else int(raw)
    except ValueError:
        raise ValueError(f"invalid_configuration:{name}") from None
    if value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f"invalid_configuration:{name}")
    return value


def _positive_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    try:
        value = default if raw is None else float(raw)
    except ValueError:
        raise ValueError(f"invalid_configuration:{name}") from None
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"invalid_configuration:{name}")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    amazon_reviews_api_base_url: str
    rag_database_url: str
    embedding_model: str = DEFAULT_MODEL
    fastembed_cache_path: str = ".cache/fastembed"
    chunk_max_tokens: int = 96
    embedding_batch_size: int = 64
    http_timeout_seconds: float = 20.0
    http_retries: int = 2
    max_response_bytes: int = 10 * 1024 * 1024
    channel_depth: int = 20
    rrf_k: int = 60
    min_rrf_score: float | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        source_url = os.getenv("AMAZON_REVIEWS_API_BASE_URL", "").strip()
        database_url = os.getenv("RAG_DATABASE_URL", "").strip()
        if not source_url.startswith(("http://", "https://")):
            raise ValueError("invalid_configuration:AMAZON_REVIEWS_API_BASE_URL")
        if not database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("invalid_configuration:RAG_DATABASE_URL")
        model_name = os.getenv("RAG_EMBEDDING_MODEL", DEFAULT_MODEL).strip()
        cache_path = os.getenv("FASTEMBED_CACHE_PATH", ".cache/fastembed").strip()
        if not model_name or not cache_path:
            raise ValueError("invalid_embedding_configuration")
        threshold_raw = os.getenv("RAG_MIN_RRF_SCORE")
        threshold = None
        if threshold_raw:
            try:
                threshold = float(threshold_raw)
            except ValueError:
                raise ValueError("invalid_configuration:RAG_MIN_RRF_SCORE") from None
            if not math.isfinite(threshold) or threshold < 0:
                raise ValueError("invalid_configuration:RAG_MIN_RRF_SCORE")
        return cls(
            amazon_reviews_api_base_url=source_url.rstrip("/"),
            rag_database_url=database_url,
            embedding_model=model_name,
            fastembed_cache_path=cache_path,
            chunk_max_tokens=_positive_int("RAG_CHUNK_MAX_TOKENS", 96, 127, minimum=16),
            embedding_batch_size=_positive_int("RAG_EMBEDDING_BATCH_SIZE", 64, 512),
            http_timeout_seconds=_positive_float("RAG_HTTP_TIMEOUT_SECONDS", 20.0),
            http_retries=_positive_int("RAG_HTTP_RETRIES", 2, 5),
            max_response_bytes=_positive_int("RAG_MAX_RESPONSE_BYTES", 10 * 1024 * 1024),
            channel_depth=_positive_int("RAG_CHANNEL_DEPTH", 20, 100),
            rrf_k=_positive_int("RAG_RRF_K", 60, 1000),
            min_rrf_score=threshold,
        )
