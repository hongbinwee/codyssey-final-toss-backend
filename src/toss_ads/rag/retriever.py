"""Product-diverse hybrid retrieval, identity guards and Commerce hydration."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict

from .chunker import is_semantic_field
from .bge_m3 import BGE_M3_MODEL, BGE_M3_MODEL_REVISION
from .commerce import CommerceStore, CommerceUnavailable
from .config import Settings
from .intent import lexical_relevance, normalized, type_registry
from .schemas import RagSearchRequest
from .source import without_user_ids
from .store import RagStore


class SearchError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def bge_profile_ready(store: RagStore, active: dict[str, Any]) -> bool:
    profile = store.embedding_profile_info(active["run_id"], BGE_M3_MODEL)
    if profile is None or (
        profile.get("status") != "ready" or profile.get("category_scope") != "*"
        or profile.get("dimension") != 1024 or profile.get("max_input_tokens") != 128
        or profile.get("model_revision") != BGE_M3_MODEL_REVISION
    ):
        return False
    try:
        target = store.embedding_target_chunk_count(active["run_id"], active["dataset_version"], "*")
        expected, stored = store.embedding_profile_counts(active["run_id"], BGE_M3_MODEL, "*")
    except ValueError:
        return False
    return target > 0 and profile.get("chunk_count") == target == expected == stored


_REVIEW_INTENT = re.compile(r"\b(?:reviews?|testimonials?)\b|리뷰|후기|사용평", re.IGNORECASE)


def _requests_review_evidence(request: RagSearchRequest) -> bool:
    return bool(_REVIEW_INTENT.search(request.original_question) or _REVIEW_INTENT.search(request.query))


def _unverified_conditions(request: RagSearchRequest) -> list[str]:
    return [*(f"확인되지 않은 필수 조건: {v}" for v in request.required_conditions),
            *(f"확인되지 않은 선호 조건: {v}" for v in request.preferences)]


def _product_metadata(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    return {k: without_user_ids(payload[k]) for k in (
        "title", "brand", "main_category", "price", "average_rating", "rating_number",
        "source_dataset", "dataset_release_status",
    ) if k in payload}


def _usable_evidence(row: dict[str, Any]) -> bool:
    text = row["evidence_text"]
    if not text.strip() or not is_semantic_field(row["source_field"]):
        return False
    # Tiny review tails retain their source provenance in the index, but are
    # not useful explanations for a shopper. New v3 chunks repair tail splits.
    return row["source_type"] != "review" or len(re.sub(r"\W", "", text)) >= 8


def _channel_candidates(store, method, run_id, query, settings, category, source_type, product_ids):
    goal = min(settings.candidate_depth, len(product_ids)) if product_ids is not None else settings.candidate_depth
    if goal == 0:
        return []
    limit = min(settings.candidate_scan_limit, max(settings.channel_depth, goal * settings.chunks_per_product))
    while True:
        args = (run_id, settings.embedding_model, query, limit, category) if method == "search_embedding_vector" else (run_id, query, limit, category)
        rows = getattr(store, method)(*args, source_type=source_type, product_ids=product_ids)
        retained = []
        counts: Counter[tuple[str, str]] = Counter()
        for row in rows:
            if category is not None and row["category"] != category:
                raise SearchError("search_failed")
            if not _usable_evidence(row):
                continue
            key = (row["category"], row["product_id"])
            if key not in counts and len(counts) >= goal:
                continue
            if counts[key] < settings.chunks_per_product:
                retained.append(row)
                counts[key] += 1
        if len(counts) >= goal or len(rows) < limit or limit >= settings.candidate_scan_limit:
            return retained
        limit = min(settings.candidate_scan_limit, limit * 2)


def hybrid_search(
    store: RagStore, embedder: Any, settings: Settings,
    request: RagSearchRequest, *, commerce: CommerceStore | None = None,
) -> dict[str, Any]:
    profile = request.profile or settings.default_profile
    base = {
        "request_id": request.request_id, "status": "error", "dataset_version": None,
        "profile_name": profile, "applied_filters": {}, "supported_categories": [],
        "unverified_conditions": _unverified_conditions(request), "items": [], "error_code": None,
        "search_context": {"ranking_version": "product-hybrid-v2", "relevance_gate": "product_identity_v2"},
    }
    if profile not in settings.allowed_profiles:
        base["error_code"] = "unsupported_profile"
        return base
    active = store.active_run(profile)
    if active is None:
        base["error_code"] = "index_not_ready"
        return base
    base["dataset_version"] = active["dataset_version"]
    supported = store.supported_categories(active["run_id"])
    base["supported_categories"] = supported
    if request.category is not None:
        if request.category not in supported:
            base["error_code"] = "unsupported_category"
            return base
        base["applied_filters"]["category"] = request.category
    uses_bge = settings.embedding_model == BGE_M3_MODEL
    if uses_bge and not bge_profile_ready(store, active):
        base["error_code"] = "index_not_ready"
        return base
    if not uses_bge and active["embedding_model"] != settings.embedding_model:
        base["error_code"] = "configuration_error"
        return base
    if request.filters.currency not in (None, "KRW"):
        base["error_code"] = "unsupported_currency"
        return base
    registry = type_registry(settings.product_type_registry_path)
    intent = registry.request_intent(request.query, request.product_type, request.original_question)
    base["search_context"].update({"product_type": intent.product_type,
        "type_origin": intent.origin, "type_registry_version": registry.version})
    catalog = store.product_catalog(active["run_id"], request.category)
    # Exact-title lookup is authoritative for identity and does not mistake
    # a bundle title with several type words for a multi-product request.
    exact = [r for r in catalog if normalized(request.query) == normalized(str(r["product_payload"].get("title", "")))]
    exact_override = (
        exact and request.product_type is None
        and normalized(request.query) in normalized(request.original_question)
        and registry.matches(request.query) == registry.matches(request.original_question)
    )
    if intent.ambiguous and not exact_override:
        base["status"] = "low_relevance"
        base["search_context"]["reason"] = "conflicting_or_ambiguous_product_type"
        return base
    if exact and request.product_type is None:
        eligible = exact
        base["search_context"]["type_origin"] = "exact_title"
    elif intent.product_type:
        scopes = registry.category_scope(intent.product_type)
        if request.category is not None and scopes and request.category not in scopes:
            base["status"] = "no_results"
            base["search_context"]["reason"] = "category_type_mismatch"
            return base
        eligible = [r for r in catalog if registry.product_matches(r["product_payload"], intent.product_type)]
        base["applied_filters"]["product_type"] = intent.product_type
        base["search_context"]["accepted_product_types"] = sorted(registry.family(intent.product_type))
    else:
        eligible = catalog
    if not eligible:
        base["status"] = "no_results"
        base["search_context"]["reason"] = "no_matching_product_type"
        return base
    # Unknown unstructured queries need a catalogue identity anchor. Vector
    # rank alone cannot prove an out-of-catalogue product is available.
    if not intent.product_type and not exact:
        eligible = [r for r in eligible if lexical_relevance(request.query, r["product_payload"])[1] > 0]
        if not eligible:
            base["status"] = "low_relevance"
            base["search_context"]["reason"] = "no_catalog_identity_match"
            return base
    stock = settings.require_in_stock if request.filters.in_stock is None else request.filters.in_stock
    constraints = stock or request.filters.price_min is not None or request.filters.price_max is not None
    checked = {}
    if commerce is not None:
        try:
            checked = commerce.lookup([
                {"product_id": row["product_id"], "category": row["category"], "payload": row["product_payload"]}
                for row in eligible
            ], request.filters, stock)
        except CommerceUnavailable as error:
            base["error_code"] = str(error)
            return base
        eligible = [r for r in eligible if (r["category"], r["product_id"]) in checked]
        if stock:
            base["applied_filters"]["in_stock"] = True
        for name in ("price_min", "price_max", "currency"):
            value = getattr(request.filters, name)
            if value is not None:
                base["applied_filters"][name] = value
        if not eligible:
            base["status"] = "no_results"
            base["search_context"]["reason"] = "no_commerce_eligible_products"
            return base
    elif constraints:
        base["error_code"] = "commerce_not_configured"
        return base
    else:
        base["unverified_conditions"].append("Commerce 가격·재고 미검증: 구매 연결 전 검증 필요")
    product_ids = list(dict.fromkeys(r["product_id"] for r in eligible))
    try:
        vector = embedder.embed_query(request.query)
        if len(vector) != (1024 if uses_bge else 384) or any(not math.isfinite(float(x)) for x in vector):
            raise ValueError("invalid_embedding")
    except Exception:
        raise SearchError("embedding_failed") from None
    vector_method = "search_embedding_vector" if uses_bge else "search_vector"
    channels = [
        ("bm25_rank", "search_bm25", request.query, None),
        ("vector_rank", vector_method, vector, None),
    ]
    if _requests_review_evidence(request):
        channels.extend([("review_bm25_rank", "search_bm25", request.query, "review"),
                         ("review_vector_rank", vector_method, vector, "review")])
    chunks: dict[str, dict[str, Any]] = {}
    product_ranks: dict[str, dict[tuple[str, str], int]] = {}
    allowed_keys = {(r["category"], r["product_id"]) for r in eligible}
    for channel, method, value, source_type in channels:
        rows = _channel_candidates(store, method, active["run_id"], value, settings,
                                   request.category, source_type, product_ids)
        distinct: dict[tuple[str, str], int] = {}
        product_ranks[channel] = distinct
        for rank, row in enumerate(rows, 1):
            key = (row["category"], row["product_id"])
            if key not in allowed_keys:
                raise SearchError("search_failed")
            distinct.setdefault(key, len(distinct) + 1)
            chunk = chunks.setdefault(row["chunk_id"], {**row, "ranks": {}, "chunk_rrf_score": 0.0})
            if (chunk["category"], chunk["product_id"], chunk["source_id"]) != (*key, row["source_id"]):
                raise SearchError("search_failed")
            chunk["ranks"][channel] = rank
            chunk["chunk_rrf_score"] += 1 / (settings.rrf_k + rank)
    products: dict[tuple[str, str], dict[str, Any]] = {}
    rejected_relevance: set[tuple[str, str]] = set()
    for chunk in chunks.values():
        key = (chunk["category"], chunk["product_id"])
        # Recheck the returned payload as well as the catalogue identity view.
        # A vector rank, review rating or cheap price cannot bypass this gate.
        payload = {**chunk["product_payload"], "category": chunk["category"]}
        if intent.product_type and not (exact and request.product_type is None):
            relevant = registry.product_matches(payload, intent.product_type)
        elif exact:
            relevant = normalized(str(payload.get("title", ""))) == normalized(request.query)
        else:
            relevant = lexical_relevance(request.query, payload)[1] > 0
        if not relevant:
            rejected_relevance.add(key)
            continue
        product = products.setdefault(key, {"product_id": key[1], "category": key[0],
            "payload": payload, "chunks": []})
        product["chunks"].append(chunk)
    products = {key: product for key, product in products.items() if key not in rejected_relevance}
    # Commerce eligibility is checked on the whole matching catalogue before
    # retrieval, so a cheap/in-stock item beyond the initial top 50 can surface.
    for key, product in products.items():
        product["rrf_score"] = sum(1 / (settings.rrf_k + ranks[key]) for ranks in product_ranks.values() if key in ranks)
        product["lexical"] = lexical_relevance(request.query, product["payload"])
    # Title/identity coverage first, then product-level RRF. Scores remain
    # explainable ranks; they are not presented as calibrated probabilities.
    ordered = sorted(products.values(), key=lambda p: (
        -p["lexical"][0], -p["lexical"][1], -p["rrf_score"], p["category"], p["product_id"]
    ))
    response_items = []
    for product in ordered:
        if settings.min_rrf_score is not None and product["rrf_score"] < settings.min_rrf_score:
            continue
        # Favor meaningful REAL reviews, and keep at least one review for
        # explicit review intent when that product has one.
        sorted_chunks = sorted(product["chunks"], key=lambda c: (
            c["source_type"] == "review" and c["source_metadata"].get("source_kind") == "SYNTHETIC",
            -c["chunk_rrf_score"], c["source_id"], c["start_offset"], c["chunk_id"]
        ))
        selection = []
        if _requests_review_evidence(request):
            review = next((c for c in sorted_chunks if c["source_type"] == "review"), None)
            if review:
                selection.append(review)
        # Different reviews provide more useful independent evidence than
        # several adjacent chunks from the same review.
        seen_reviews = {c["source_id"] for c in selection}
        for chunk in sorted_chunks:
            if chunk in selection or (chunk["source_type"] == "review" and chunk["source_id"] in seen_reviews):
                continue
            selection.append(chunk)
            if chunk["source_type"] == "review":
                seen_reviews.add(chunk["source_id"])
            if len(selection) >= 3:
                break
        if not selection:
            continue
        evidence = [{
            "product_id": product["product_id"], "chunk_id": c["chunk_id"],
            "source_type": c["source_type"], "source_id": c["source_id"],
            "source_field": c["source_field"], "source_version": active["dataset_version"],
            "evidence_text": c["evidence_text"], "source_metadata": without_user_ids(c["source_metadata"]),
            "start_offset": c["start_offset"], "end_offset": c["end_offset"],
            "bm25_rank": c["ranks"].get("bm25_rank"), "vector_rank": c["ranks"].get("vector_rank"),
            "review_bm25_rank": c["ranks"].get("review_bm25_rank"),
            "review_vector_rank": c["ranks"].get("review_vector_rank"),
            "rrf_rank": len(response_items) + 1,
        } for c in selection]
        metadata = _product_metadata(product["payload"])
        commerce_result = checked.get((product["category"], product["product_id"]))
        if commerce_result:
            # Do not show a stale/cheaper sold-out option as the recommended price.
            metadata["price"] = {"amount_won": commerce_result["unit_price_won"], "currency": "KRW",
                "price_basis": "selected_commerce_variant", "is_simulated": commerce_result["is_simulated"],
                "is_live_market_price": False,
                "evidence_status": commerce_result["source_price_evidence_status"]}
        response_items.append({"product_id": product["product_id"], "category": product["category"],
            "product_metadata": metadata, "rrf_score": product["rrf_score"], "evidence": evidence,
            "commerce": commerce_result or {"validation_status": "unverified"},
            "ranking": {"title_identity_match": product["lexical"][0], "lexical_coverage": product["lexical"][1],
                "relevance_qualified": True, "requested_product_type": intent.product_type},
        })
        if len(response_items) >= request.top_k:
            break
    base["search_context"].update({"eligible_catalog_products": len(eligible),
        "retrieved_products": len({(c["category"], c["product_id"]) for c in chunks.values()}),
        "commerce_eligible_products": len(products) if commerce is not None else None})
    base["search_context"]["relevance_rejected_products"] = len(rejected_relevance)
    if not response_items:
        base["status"] = "no_results"
        base["search_context"]["reason"] = "no_eligible_candidates"
        return base
    base["status"] = "ok"
    base["items"] = response_items
    return base


class HybridRagRetriever(BaseRetriever):
    """LangChain Core adapter returning source-grounded evidence Documents."""

    store: RagStore
    embedder: Any
    settings: Settings
    commerce: CommerceStore | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        request = RagSearchRequest(original_question=query, query=query, top_k=10)
        response = hybrid_search(self.store, self.embedder, self.settings, request, commerce=self.commerce)
        if response["status"] != "ok":
            return []
        return [
            Document(
                page_content=evidence["evidence_text"],
                metadata={
                    **evidence,
                    "category": product["category"],
                    "product_metadata": product["product_metadata"],
                    "product_rrf_score": product["rrf_score"],
                },
            )
            for product in response["items"]
            for evidence in product["evidence"]
        ]
