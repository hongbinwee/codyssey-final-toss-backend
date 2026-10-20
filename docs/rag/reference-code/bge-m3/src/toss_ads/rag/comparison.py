"""Offline BM25, dense, and hybrid comparison retrieval."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal


RetrievalMode = Literal["bm25", "hybrid", "dense"]


def _product_metadata(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    allowed = ("title", "brand", "main_category", "price", "average_rating", "rating_number")
    return {key: payload[key] for key in allowed if key in payload}


def search_products(
    store: Any,
    embedder: Any,
    *,
    run_id: str,
    query: str,
    mode: RetrievalMode,
    category: str,
    channel_depth: int = 20,
    rrf_k: int = 60,
) -> list[dict[str, Any]]:
    if mode not in ("bm25", "hybrid", "dense"):
        raise ValueError("invalid_retrieval_mode")
    if channel_depth <= 0 or rrf_k <= 0:
        raise ValueError("invalid_retrieval_configuration")

    channels: list[tuple[str, Sequence[dict[str, Any]]]] = []
    if mode in ("bm25", "hybrid"):
        channels.append(
            ("bm25", store.search_bm25(run_id, query, channel_depth, category))
        )
    if mode in ("dense", "hybrid"):
        vector = embedder.embed_query(query)
        if len(vector) != 1024:
            raise ValueError("embedding_dimension_mismatch")
        model_name = getattr(embedder, "model_name", "BAAI/bge-m3")
        channels.append(
            (
                "dense",
                store.search_embedding_vector(
                    run_id, model_name, vector, channel_depth, category
                ),
            )
        )

    products: dict[tuple[str, str], dict[str, Any]] = {}
    for channel, rows in channels:
        if len(rows) > channel_depth:
            raise ValueError("retrieval_channel_limit_exceeded")
        for rank, row in enumerate(rows, start=1):
            if row.get("category") != category:
                raise ValueError("retrieval_scope_mismatch")
            key = (row["category"], row["product_id"])
            product = products.setdefault(
                key,
                {
                    "category": row["category"],
                    "product_id": row["product_id"],
                    "product_metadata": _product_metadata(row.get("product_payload")),
                    "best_rank_by_channel": {"bm25": None, "dense": None},
                    "score": 0.0,
                    "evidence": [],
                    "_evidence_chunk_ids": set(),
                },
            )
            # A product contributes only its first chunk rank within each channel.
            if product["best_rank_by_channel"][channel] is not None:
                continue
            product["best_rank_by_channel"][channel] = rank
            product["score"] += 1.0 / (rrf_k + rank)
            chunk_id = row.get("chunk_id")
            if chunk_id not in product["_evidence_chunk_ids"]:
                product["_evidence_chunk_ids"].add(chunk_id)
                product["evidence"].append(
                    {
                        "chunk_id": chunk_id,
                        "source_type": row.get("source_type"),
                        "source_id": row.get("source_id"),
                        "source_field": row.get("source_field"),
                        "evidence_text": row.get("evidence_text"),
                        "rank_channel": channel,
                        "rank": rank,
                    }
                )

    ordered = sorted(
        products.values(),
        key=lambda product: (
            -product["score"],
            product["category"],
            product["product_id"],
        ),
    )
    for product in ordered:
        product.pop("_evidence_chunk_ids", None)
    return ordered
