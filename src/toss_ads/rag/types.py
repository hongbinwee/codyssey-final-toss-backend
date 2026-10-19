"""Typed values shared by the source client, indexer, store, and retriever."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class EvidenceChunk:
    chunk_id: str
    dataset_version: str
    category: str
    product_id: str
    source_type: str
    source_id: str
    source_field: str
    start_offset: int
    end_offset: int
    evidence_text: str
    embedding_text: str
    source_metadata: dict[str, object]
    embedding_model: str
    chunker_version: str


@dataclass(frozen=True, slots=True)
class CategorySnapshot:
    dataset_version: str
    categories: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class IndexedProduct:
    dataset_version: str
    category: str
    product_id: str
    product_payload: dict[str, Any]
    price_amount: Decimal | None = None
    price_currency: str | None = None


@dataclass(frozen=True, slots=True)
class QuarantinedProduct:
    dataset_version: str
    category: str
    product_id: str
    reason_code: str
    policy_version: str
    product_title: str | None
    main_category: str | None
    categories: tuple[str, ...]
    type_signals: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IndexCounts:
    product_count: int
    review_count: int
    chunk_count: int
    category_counts: dict[str, dict[str, int]]


@dataclass(frozen=True, slots=True)
class IndexSummary:
    run_id: str
    dataset_version: str
    status: str
    counts: IndexCounts


@dataclass(frozen=True, slots=True)
class RankedChunk:
    chunk_id: str
    category: str
    product_id: str
    source_type: str
    source_id: str
    source_field: str
    start_offset: int
    end_offset: int
    evidence_text: str
    source_metadata: dict[str, Any]
    product_metadata: dict[str, Any]
    bm25_rank: int | None = None
    vector_rank: int | None = None
    rrf_score: float = 0.0
    rrf_rank: int | None = None
