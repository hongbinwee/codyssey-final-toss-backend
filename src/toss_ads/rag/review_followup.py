"""Product-scoped review retrieval and full-corpus aspect aggregation."""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections import defaultdict
from typing import Any

from .bge_m3 import BGE_M3_MODEL
from .chunker import is_semantic_field
from .schemas import ProductScopedReviewAggregateRequest, ProductScopedReviewRequest
from .source import without_user_ids
from .store import RagStore


ASPECT_TAXONOMY_VERSION = "qa13-review-aspects-v1"
_ASPECTS: dict[str, dict[str, Any]] = {
    "moisturizing": {
        "label": "보습·촉촉함",
        "aliases": ("moisturizing", "moisturizer", "moisturising", "moisturiser", "hydration", "hydrating", "보습", "보습력", "촉촉함", "촉촉"),
        "query_terms": ("보습", "촉촉", "수분감", "건조하지 않음", "당김", "피부가 편안함"),
    }
}
_POLARITIES = ("positive", "negative", "mixed", "neutral", "not_mentioned", "unclassified")
SUPPORTED_REVIEW_ASPECTS = tuple(_ASPECTS)
SUPPORTED_REVIEW_POLARITIES = _POLARITIES


class ReviewFeatureError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _canonical_aspect(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    for canonical, definition in _ASPECTS.items():
        if normalized == canonical or normalized in definition["aliases"]:
            return canonical
    raise ReviewFeatureError("unsupported_aspect")


def _review_id(dataset_version: str, category: str, product_id: str, source_id: str) -> str:
    stable_key = json.dumps(
        [dataset_version, category, product_id, source_id],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(stable_key.encode("utf-8")).hexdigest()


def _scope_products(
    store: RagStore,
    active: dict[str, Any],
    product_ids: list[str],
    requested_category: str | None,
    expected_dataset_version: str | None,
) -> list[dict[str, Any]]:
    if expected_dataset_version is not None and expected_dataset_version != active["dataset_version"]:
        raise ReviewFeatureError("dataset_version_mismatch")
    categories = store.supported_categories(active["run_id"])
    if requested_category is not None and requested_category not in categories:
        raise ReviewFeatureError("unsupported_category")
    catalog = store.product_catalog(active["run_id"], requested_category)
    by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in catalog:
        by_id[row["product_id"]].append(row)
    selected: list[dict[str, Any]] = []
    for product_id in product_ids:
        matches = by_id.get(product_id, [])
        if not matches:
            raise ReviewFeatureError("unknown_product_id")
        if len(matches) != 1:
            raise ReviewFeatureError("ambiguous_product_id")
        selected.append(matches[0])
    return selected


def _check_index_ready(store: RagStore, settings: Any, active: dict[str, Any]) -> bool:
    uses_bge = settings.embedding_model == BGE_M3_MODEL
    if uses_bge:
        from .retriever import bge_profile_ready

        if not bge_profile_ready(store, active):
            raise ReviewFeatureError("index_not_ready")
    elif active["embedding_model"] != settings.embedding_model:
        raise ReviewFeatureError("configuration_error")
    return uses_bge


def _usable_review_chunk(row: dict[str, Any]) -> bool:
    text = row.get("evidence_text")
    return (
        isinstance(text, str)
        and bool(text.strip())
        and is_semantic_field(str(row.get("source_field", "")))
        and len(re.sub(r"\W", "", text)) >= 8
    )


def _rank_reviews(rows: list[dict[str, Any]]) -> list[tuple[str, int, dict[str, Any]]]:
    """Convert chunk ranks to unique-review ranks, retaining one citation chunk."""
    selected: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not _usable_review_chunk(row):
            continue
        selected.setdefault(row["source_id"], row)
    return [(source_id, rank, row) for rank, (source_id, row) in enumerate(selected.items(), 1)]


def _product_metadata(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    return {key: without_user_ids(payload[key]) for key in ("title", "brand", "main_category") if key in payload}


def search_product_reviews(
    store: RagStore,
    embedder: Any,
    settings: Any,
    request: ProductScopedReviewRequest,
) -> dict[str, Any]:
    profile = request.profile or settings.default_profile
    if profile not in settings.allowed_profiles:
        raise ReviewFeatureError("unsupported_profile")
    aspect = _canonical_aspect(request.aspect)
    active = store.active_run(profile)
    if active is None:
        raise ReviewFeatureError("index_not_ready")
    selected = _scope_products(
        store, active, request.product_ids, request.category, request.dataset_version
    )
    uses_bge = _check_index_ready(store, settings, active)
    definition = _ASPECTS[aspect]
    query = " ".join(dict.fromkeys([request.query, definition["label"], *definition["query_terms"]]))
    try:
        vector = embedder.embed_query(query)
        expected_dimension = 1024 if uses_bge else 384
        if len(vector) != expected_dimension or any(not math.isfinite(float(x)) for x in vector):
            raise ValueError("invalid_embedding")
    except Exception:
        raise ReviewFeatureError("embedding_failed") from None

    vector_method = "search_embedding_vector" if uses_bge else "search_vector"
    candidate_limit = min(
        settings.candidate_scan_limit,
        max(24, request.limit_per_product * settings.chunks_per_product * 8),
    )
    items: list[dict[str, Any]] = []
    for product in selected:
        product_id = product["product_id"]
        category = product["category"]
        channel_rows = {
            "bm25": store.search_bm25(
                active["run_id"], query, candidate_limit, category, "review", [product_id]
            ),
            "vector": getattr(store, vector_method)(
                active["run_id"], *(
                    (settings.embedding_model, vector, candidate_limit, category)
                    if uses_bge
                    else (vector, candidate_limit, category)
                ),
                source_type="review",
                product_ids=[product_id],
            ),
        }

        review_scores: dict[str, float] = defaultdict(float)
        chunk_rows: dict[str, dict[str, Any]] = {}
        review_chunk_scores: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for channel, rows in channel_rows.items():
            ranked = _rank_reviews(rows)
            for source_id, rank, row in ranked:
                if row["product_id"] != product_id or row["category"] != category:
                    raise ReviewFeatureError("search_failed")
                review_scores[source_id] += 1 / (settings.rrf_k + rank)
                review_chunk_scores[source_id][row["chunk_id"]] += 1 / (settings.rrf_k + rank)
                chunk_rows.setdefault(row["chunk_id"], row)

        ordered_sources = sorted(
            review_scores,
            key=lambda source_id: (-review_scores[source_id], source_id),
        )[: request.limit_per_product]
        reviews: list[dict[str, Any]] = []
        annotation_map = store.review_aspect_labels_for_sources(
            active["run_id"],
            profile,
            active["dataset_version"],
            category,
            product_id,
            ordered_sources,
            aspect,
            ASPECT_TAXONOMY_VERSION,
        ) if ordered_sources else {}
        for source_id in ordered_sources:
            chunk_id = min(
                review_chunk_scores[source_id],
                key=lambda value: (-review_chunk_scores[source_id][value], value),
            )
            row = chunk_rows[chunk_id]
            metadata = without_user_ids(row["source_metadata"])
            annotation = annotation_map.get(source_id)
            citation = {
                "evidence_id": row["chunk_id"],
                "source_field": row["source_field"],
                "source_version": active["dataset_version"],
                "evidence_text": row["evidence_text"],
                "start_offset": row["start_offset"],
                "end_offset": row["end_offset"],
            }
            reviews.append({
                "review_id": _review_id(active["dataset_version"], category, product_id, source_id),
                "product_id": product_id,
                "category": category,
                "source_kind": metadata.get("source_kind"),
                "rating": metadata.get("rating"),
                "written_at": metadata.get("timestamp"),
                "rrf_score": review_scores[source_id],
                "aspect_sentiment": annotation,
                "evidence": [citation],
            })
        payload = product.get("product_payload")
        items.append({
            "product_id": product_id,
            "category": category,
            "product_metadata": _product_metadata(payload),
            "reviews": reviews,
        })

    found = sum(len(item["reviews"]) for item in items)
    return {
        "request_id": request.request_id,
        "status": "ok" if found else "no_results",
        "profile_name": profile,
        "dataset_version": active["dataset_version"],
        "aspect": {"id": aspect, "label": definition["label"], "taxonomy_version": ASPECT_TAXONOMY_VERSION},
        "search_context": {
            "ranking_version": "product-scoped-review-hybrid-v1",
            "channels": ["bm25", "bge_m3" if uses_bge else "vector"],
            "result_limit_semantics": "reviews_per_product",
            "polarity_source": "versioned_aspect_annotations_when_available",
        },
        "items": items,
    }


def aggregate_product_reviews(
    store: RagStore,
    settings: Any,
    request: ProductScopedReviewAggregateRequest,
) -> dict[str, Any]:
    profile = request.profile or settings.default_profile
    if profile not in settings.allowed_profiles:
        raise ReviewFeatureError("unsupported_profile")
    aspect = _canonical_aspect(request.aspect)
    active = store.active_run(profile)
    if active is None:
        raise ReviewFeatureError("index_not_ready")
    selected = _scope_products(
        store, active, request.product_ids, request.category, request.dataset_version
    )
    by_category: dict[str, list[str]] = defaultdict(list)
    for product in selected:
        by_category[product["category"]].append(product["product_id"])

    aggregates: dict[tuple[str, str], dict[str, Any]] = {}
    for category, product_ids in by_category.items():
        result = store.review_aspect_aggregate(
            active["run_id"],
            profile,
            active["dataset_version"],
            category,
            product_ids,
            aspect,
            ASPECT_TAXONOMY_VERSION,
        )
        batch = result["batch"]
        for row in result["items"]:
            population = int(row["review_population_count"])
            annotated = int(row["annotated_review_count"])
            coverage = 1.0 if population == 0 else annotated / population
            ready = (
                batch is not None
                and int(batch["expected_review_count"]) == int(batch["labeled_review_count"])
                and int(batch["current_review_count"]) == int(batch["expected_review_count"])
                and int(batch["aspect_review_count"]) == int(batch["expected_review_count"])
                and annotated == population
            )
            counts = None
            reason = None
            if ready:
                counts = {polarity: int(row[f"{polarity}_count"]) for polarity in _POLARITIES}
                mentioned = sum(counts[key] for key in ("positive", "negative", "mixed", "neutral"))
                counts["aspect_mentioned_review_count"] = mentioned
                counts["positive_rate_among_classified_mentions"] = (
                    counts["positive"] / mentioned if mentioned else None
                )
            elif batch is None:
                reason = "aspect_annotations_not_loaded"
            else:
                reason = "incomplete_annotation_coverage"
            unclassified = int(row.get("unclassified_count") or 0)
            classified = max(0, annotated - unclassified)
            aggregates[(category, row["product_id"])] = {
                "aggregation_status": "ready" if ready else "unavailable",
                "reason": reason,
                "review_population_count": population,
                "annotated_review_count": annotated,
                "coverage_ratio": coverage,
                "classified_review_count": classified,
                "classification_coverage_ratio": classified / population if population else None,
                "unclassified_review_count": unclassified,
                "counts": counts,
                "annotation_version": (
                    {"batch_id": batch["batch_id"],
                     "taxonomy_version": batch["taxonomy_version"],
                     "classifier_version": batch["classifier_version"]}
                    if batch is not None else None
                ),
            }

    items = []
    for product in selected:
        data = aggregates[(product["category"], product["product_id"])]
        items.append({"product_id": product["product_id"], "category": product["category"], **data})
    return {
        "request_id": request.request_id,
        "status": "ok" if all(row["aggregation_status"] == "ready" for row in items) else "aggregation_unavailable",
        "profile_name": profile,
        "dataset_version": active["dataset_version"],
        "aspect": {"id": aspect, "label": _ASPECTS[aspect]["label"], "taxonomy_version": ASPECT_TAXONOMY_VERSION},
        "label_quality": "not_human_validated",
        "count_semantics": "full_population_unique_review_labels; not verified ground truth",
        "deduplication": "one record per product_id + source review_key; chunk count is not review count",
        "items": items,
    }
