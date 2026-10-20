"""Environment-backed runtime configuration with no secret-bearing repr."""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlsplit


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
    rag_database_url: str = field(repr=False)
    embedding_model: str = DEFAULT_MODEL
    fastembed_cache_path: str = ".cache/fastembed"
    bge_m3_cache_path: str = ".cache/fastembed/huggingface"
    chunk_max_tokens: int = 96
    embedding_batch_size: int = 64
    http_timeout_seconds: float = 20.0
    http_retries: int = 2
    max_response_bytes: int = 10 * 1024 * 1024
    channel_depth: int = 20
    rrf_k: int = 60
    min_rrf_score: float | None = None
    default_profile: str = "all_products"
    allowed_profiles: tuple[str, ...] = ("all_products", "test_items2")
    commerce_database_url: str = field(default="", repr=False)
    commerce_schema_map: tuple[tuple[str, str], ...] = (
        ("test_items2", "test_items2"), ("test_items", "test_items"),
        ("test_earphones", "test_earphones"), ("commerce", "public"),
    )
    require_in_stock: bool = True
    candidate_depth: int = 50
    chunks_per_product: int = 3
    candidate_scan_limit: int = 2000
    product_type_registry_path: str | None = None

    def __post_init__(self) -> None:
        for url, database in ((self.rag_database_url, "toss_rag"), (self.commerce_database_url, "toss")):
            if url:
                try:
                    parsed = urlsplit(url)
                    valid = (
                        parsed.scheme in {"postgres", "postgresql"}
                        and bool(parsed.hostname) and "," not in parsed.hostname
                        and parsed.port in (None, 5432) and parsed.path == "/" + database
                        and not {"host", "hostaddr", "port", "dbname", "service"}.intersection(parse_qs(parsed.query))
                    )
                except ValueError:
                    valid = False
                if not valid:
                    raise ValueError("invalid_configuration:database_endpoint")
        if self.default_profile not in self.allowed_profiles:
            raise ValueError("invalid_configuration:RAG_DEFAULT_PROFILE")
        if not 1 <= self.candidate_depth <= 100 or not 1 <= self.chunks_per_product <= 5:
            raise ValueError("invalid_configuration:candidate_limits")
        if self.rrf_k <= 0 or self.channel_depth <= 0:
            raise ValueError("invalid_configuration:ranking_limits")
        if not self.candidate_depth <= self.candidate_scan_limit <= 10000:
            raise ValueError("invalid_configuration:RAG_CANDIDATE_SCAN_LIMIT")
        if len(dict(self.commerce_schema_map)) != len(self.commerce_schema_map) or any(
            not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", part)
            for pair in self.commerce_schema_map for part in pair
        ):
            raise ValueError("invalid_configuration:COMMERCE_SCHEMA_MAP")

    @classmethod
    def from_env(cls) -> "Settings":
        database_url = os.getenv("RAG_DATABASE_URL", "").strip()
        if not database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("invalid_configuration:RAG_DATABASE_URL")
        model_name = os.getenv("RAG_EMBEDDING_MODEL", DEFAULT_MODEL).strip()
        cache_path = os.getenv("FASTEMBED_CACHE_PATH", ".cache/fastembed").strip()
        bge_cache_path = os.getenv("BGE_M3_CACHE_PATH", os.path.join(cache_path, "huggingface")).strip()
        if not model_name or not cache_path or not bge_cache_path:
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
        default_profile = os.getenv("RAG_DEFAULT_PROFILE", "all_products").strip()
        if not default_profile or len(default_profile) > 128:
            raise ValueError("invalid_configuration:RAG_DEFAULT_PROFILE")
        allowed_profiles = tuple(x.strip() for x in os.getenv(
            "RAG_ALLOWED_PROFILES", "all_products,test_items2"
        ).split(",") if x.strip())
        if any(len(x) > 128 for x in allowed_profiles):
            raise ValueError("invalid_configuration:RAG_ALLOWED_PROFILES")
        stock = os.getenv("RAG_REQUIRE_IN_STOCK", "true").lower()
        if stock not in {"true", "false"}:
            raise ValueError("invalid_configuration:RAG_REQUIRE_IN_STOCK")
        schema_pairs = tuple(tuple(x.strip().split(":")) for x in os.getenv(
            "COMMERCE_SCHEMA_MAP", "test_items2:test_items2,test_items:test_items,test_earphones:test_earphones,commerce:public"
        ).split(",") if x.strip())
        if any(len(x) != 2 for x in schema_pairs):
            raise ValueError("invalid_configuration:COMMERCE_SCHEMA_MAP")
        return cls(
            rag_database_url=database_url,
            embedding_model=model_name,
            fastembed_cache_path=cache_path,
            bge_m3_cache_path=bge_cache_path,
            chunk_max_tokens=_positive_int("RAG_CHUNK_MAX_TOKENS", 96, 127, minimum=16),
            embedding_batch_size=_positive_int("RAG_EMBEDDING_BATCH_SIZE", 64, 512),
            http_timeout_seconds=_positive_float("RAG_HTTP_TIMEOUT_SECONDS", 20.0),
            http_retries=_positive_int("RAG_HTTP_RETRIES", 2, 5),
            max_response_bytes=_positive_int("RAG_MAX_RESPONSE_BYTES", 10 * 1024 * 1024),
            channel_depth=_positive_int("RAG_CHANNEL_DEPTH", 20, 100),
            rrf_k=_positive_int("RAG_RRF_K", 60, 1000),
            min_rrf_score=threshold,
            default_profile=default_profile,
            allowed_profiles=allowed_profiles,
            commerce_database_url=os.getenv("COMMERCE_DATABASE_URL", "").strip(),
            commerce_schema_map=schema_pairs,
            require_in_stock=stock == "true",
            candidate_depth=_positive_int("RAG_CANDIDATE_DEPTH", 50, 100),
            chunks_per_product=_positive_int("RAG_CHUNKS_PER_PRODUCT", 3, 5),
            candidate_scan_limit=_positive_int("RAG_CANDIDATE_SCAN_LIMIT", 2000, 10000),
            product_type_registry_path=os.getenv("RAG_PRODUCT_TYPE_REGISTRY") or None,
        )
