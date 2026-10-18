"""BM25 + cosine retrieval, product-level RRF, and LangChain adapter."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnableConfig
from pydantic import ConfigDict, Field, PrivateAttr

from .config import Settings
from .schemas import RagSearchRequest
from .source import without_user_ids
from .store import RagStore

logger = logging.getLogger("toss_ads.rag.retriever")


class SearchError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


_REVIEW_INTENT = re.compile(r"\b(?:reviews?|testimonials?)\b|리뷰|후기|사용평", re.IGNORECASE)


def _requests_review_evidence(request: RagSearchRequest) -> bool:
    return bool(
        _REVIEW_INTENT.search(request.original_question)
        or _REVIEW_INTENT.search(request.query)
    )


def _unverified_conditions(request: RagSearchRequest) -> list[str]:
    conditions: list[str] = []
    filters = request.filters
    if filters.price_min is not None or filters.price_max is not None:
        low = "없음" if filters.price_min is None else str(filters.price_min)
        high = "없음" if filters.price_max is None else str(filters.price_max)
        currency = filters.currency or "통화 미지정"
        conditions.append(
            f"가격 범위 {low}–{high} {currency}: 원본 통화/비교 기준이 확인되지 않아 적용하지 않음"
        )
    conditions.extend(f"확인되지 않은 필수 조건: {value}" for value in request.required_conditions)
    conditions.extend(f"확인되지 않은 선호 조건: {value}" for value in request.preferences)
    return conditions


def _product_metadata(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    allowed = (
        "title",
        "brand",
        "main_category",
        "price",
        "average_rating",
        "rating_number",
        "image_urls",
        "description",
    )
    return {
        key: without_user_ids(payload[key])
        for key in allowed
        if key in payload
    }


def hybrid_search(
    store: RagStore,
    embedder: FastEmbedEmbeddings,
    settings: Settings,
    request: RagSearchRequest,
) -> dict[str, Any]:
    base = {
        "request_id": request.request_id,
        "status": "error",
        "dataset_version": None,
        "applied_filters": {},
        "supported_categories": [],
        "unverified_conditions": _unverified_conditions(request),
        "items": [],
        "error_code": None,
    }
    active = store.active_run(settings.default_profile)
    if active is None:
        base["error_code"] = "index_not_ready"
        return base
    base["dataset_version"] = active["dataset_version"]
    category_reader = getattr(store, "supported_categories", None)
    supported_categories = (
        category_reader(active["run_id"]) if callable(category_reader) else []
    )
    base["supported_categories"] = supported_categories
    if request.category is not None:
        if request.category not in supported_categories:
            base["error_code"] = "unsupported_category"
            return base
        base["applied_filters"] = {"category": request.category}
    if active["embedding_model"] != settings.embedding_model:
        base["error_code"] = "configuration_error"
        return base
    try:
        try:
            vector = embedder.embed_query(request.query)
        except Exception:
            raise SearchError("embedding_failed") from None
        if len(vector) != 384:
            raise SearchError("embedding_failed")
        bm25_rows = store.search_bm25(
            active["run_id"], request.query, settings.channel_depth, request.category
        )
        vector_rows = store.search_vector(
            active["run_id"], vector, settings.channel_depth, request.category
        )
        retrieval_channels = [
            ("bm25_rank", bm25_rows),
            ("vector_rank", vector_rows),
        ]
        if _requests_review_evidence(request):
            retrieval_channels.extend(
                [
                    (
                        "review_bm25_rank",
                        store.search_bm25(
                            active["run_id"],
                            request.query,
                            settings.channel_depth,
                            request.category,
                            source_type="review",
                        ),
                    ),
                    (
                        "review_vector_rank",
                        store.search_vector(
                            active["run_id"],
                            vector,
                            settings.channel_depth,
                            request.category,
                            source_type="review",
                        ),
                    ),
                ]
            )
    except SearchError:
        raise

    chunks: dict[str, dict[str, Any]] = {}
    for channel, rows in retrieval_channels:
        for rank, row in enumerate(rows, start=1):
            if request.category is not None and row["category"] != request.category:
                raise SearchError("search_failed")
            chunk_id = row["chunk_id"]
            item = chunks.setdefault(
                chunk_id,
                {
                    **row,
                    "bm25_rank": None,
                    "vector_rank": None,
                    "review_bm25_rank": None,
                    "review_vector_rank": None,
                    "chunk_rrf_score": 0.0,
                },
            )
            identity = (item["category"], item["product_id"], item["source_id"])
            if identity != (row["category"], row["product_id"], row["source_id"]):
                raise SearchError("search_failed")
            item[channel] = rank
            item["chunk_rrf_score"] += 1.0 / (settings.rrf_k + rank)

    products: dict[tuple[str, str], dict[str, Any]] = {}
    for chunk in chunks.values():
        key = (chunk["category"], chunk["product_id"])
        product = products.setdefault(
            key,
            {
                "product_id": chunk["product_id"],
                "category": chunk["category"],
                "product_metadata": _product_metadata(chunk["product_payload"]),
                "best_bm25_rank": None,
                "best_vector_rank": None,
                "rrf_score": 0.0,
                "chunks": [],
            },
        )
        if chunk["bm25_rank"] is not None:
            best = product["best_bm25_rank"]
            product["best_bm25_rank"] = min(best, chunk["bm25_rank"]) if best else chunk["bm25_rank"]
        if chunk["vector_rank"] is not None:
            best = product["best_vector_rank"]
            product["best_vector_rank"] = min(best, chunk["vector_rank"]) if best else chunk["vector_rank"]
        product["chunks"].append(chunk)

    for product in products.values():
        for rank in (product["best_bm25_rank"], product["best_vector_rank"]):
            if rank is not None:
                product["rrf_score"] += 1.0 / (settings.rrf_k + rank)

    ordered_products = [
        product
        for product in sorted(
            products.values(),
            key=lambda item: (-item["rrf_score"], item["category"], item["product_id"]),
        )
        if any(
            chunk["bm25_rank"] is not None or chunk["vector_rank"] is not None
            for chunk in product["chunks"]
        )
    ][: request.top_k]
    response_items: list[dict[str, Any]] = []
    for product_rank, product in enumerate(ordered_products, start=1):
        ordered_chunks = sorted(
            product["chunks"],
            key=lambda item: (
                -item["chunk_rrf_score"],
                item["source_type"],
                item["source_id"],
                item["start_offset"],
                item["chunk_id"],
            ),
        )
        evidence = []
        for chunk in ordered_chunks:
            if chunk["bm25_rank"] is None and chunk["vector_rank"] is None:
                continue
            evidence.append(
                {
                    "product_id": product["product_id"],
                    "chunk_id": chunk["chunk_id"],
                    "source_type": chunk["source_type"],
                    "source_id": chunk["source_id"],
                    "source_field": chunk["source_field"],
                    "source_version": active["dataset_version"],
                    "evidence_text": chunk["evidence_text"],
                    "source_metadata": without_user_ids(chunk["source_metadata"]),
                    "start_offset": chunk["start_offset"],
                    "end_offset": chunk["end_offset"],
                    "bm25_rank": chunk["bm25_rank"],
                    "vector_rank": chunk["vector_rank"],
                    "rrf_rank": product_rank,
                }
            )
            if len(evidence) == 3:
                break
        if evidence:
            response_items.append(
                {
                    "product_id": product["product_id"],
                    "category": product["category"],
                    "product_metadata": product["product_metadata"],
                    "rrf_score": product["rrf_score"],
                    "evidence": evidence,
                }
            )

    if not response_items:
        base["status"] = "no_results"
        return base
    threshold = settings.min_rrf_score
    if threshold is not None and all(item["rrf_score"] < threshold for item in response_items):
        base["status"] = "low_relevance"
        return base
    base["status"] = "ok"
    base["items"] = response_items
    return base


class HybridRagRetriever(BaseRetriever):
    """LangChain retrieval with Documents and a request-scoped HTTP artifact."""

    store: RagStore
    embedder: FastEmbedEmbeddings
    settings: Settings
    search_request: RagSearchRequest | None = Field(default=None, exclude=True, repr=False)
    _search_response: dict[str, Any] | None = PrivateAttr(default=None)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def search(
        self, request: RagSearchRequest, *, config: RunnableConfig | None = None,
    ) -> dict[str, Any]:
        """Run the LangChain lifecycle while retaining the complete API response.

        A fresh scope keeps structured inputs and response artifacts independent
        when the application shares this retriever across concurrent requests.
        """
        scoped = self.model_copy(update={"search_request": request.model_copy(deep=True)})
        scoped._search_response = None
        try:
            scoped.invoke(request.query, config=config)
        except SearchError:
            # LangChain callers see an error; HTTP callers retain its full
            # status, dataset version, supported categories and conditions.
            if scoped._search_response is None or scoped._search_response["status"] != "error":
                raise
        if scoped._search_response is None:
            raise SearchError("search_failed")
        return scoped._search_response

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        request = (
            self.search_request.model_copy(update={"query": query})
            if self.search_request is not None
            else RagSearchRequest(original_question=query, query=query, top_k=10)
        )
        logger.info("langchain_retriever %s", json.dumps({
            "event": "start", "request_id": request.request_id,
            "category": request.category, "top_k": request.top_k,
        }, ensure_ascii=False))
        response = hybrid_search(self.store, self.embedder, self.settings, request)
        self._search_response = response
        logger.info("langchain_retriever %s", json.dumps({
            "event": "result", "request_id": request.request_id,
            "status": response["status"], "dataset_version": response["dataset_version"],
        }, ensure_ascii=False))
        if response["status"] == "error":
            raise SearchError(response["error_code"] or "search_failed")
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
