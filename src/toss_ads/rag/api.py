"""FastAPI boundary for the Agent-to-RAG v0.1 request/response contract."""

from __future__ import annotations

import json
import hashlib
import logging
import re
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from pydantic import ValidationError

from .commerce import CommerceStore
from .bge_m3 import BGE_M3_MODEL
from .config import Settings
from .embeddings import create_embedder
from .intent import type_registry
from .retriever import SearchError, bge_profile_ready, hybrid_search
from .review_followup import (
    ReviewFeatureError,
    aggregate_product_reviews,
    search_product_reviews,
)
from .schemas import (
    ProductScopedReviewAggregateRequest,
    ProductScopedReviewRequest,
    RagSearchRequest,
)
from .store import RagStore

logger = logging.getLogger("toss_ads.rag")
MAX_REQUEST_BYTES = 64 * 1024
TEST_ITEMS_DATASET_VERSION = (
    "test_items:sha256=4e9924492dcb536e:products=180:reviews=4737"
)
TEST_ITEMS_CATEGORY = "beauty"


def _error_response(request_id: str | None, error_code: str) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "status": "error",
        "dataset_version": None,
        "applied_filters": {},
        "supported_categories": [],
        "unverified_conditions": [],
        "items": [],
        "error_code": error_code,
    }


def _safe_request_id(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return re.sub(r"[\x00-\x1f\x7f]", " ", value[:128])


def _status_code(error_code: str | None) -> int:
    return {
        "invalid_request": 422,
        "unsupported_category": 422,
        "unsupported_profile": 422,
        "unsupported_currency": 422,
        "commerce_not_configured": 503,
        "commerce_source_unmapped": 503,
        "index_not_ready": 503,
        "embedding_failed": 503,
        "database_failed": 503,
        "configuration_error": 503,
        "timeout": 504,
    }.get(error_code, 500)


def _review_status_code(error_code: str | None) -> int:
    return {
        "invalid_request": 422,
        "unsupported_profile": 422,
        "unsupported_category": 422,
        "unsupported_aspect": 422,
        "unknown_product_id": 422,
        "ambiguous_product_id": 422,
        "dataset_version_mismatch": 409,
        "index_not_ready": 503,
        "configuration_error": 503,
        "embedding_failed": 503,
        "annotation_schema_not_ready": 503,
        "database_failed": 503,
        "timeout": 504,
    }.get(error_code, 500)


def _review_error_response(request_id: str | None, error_code: str) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "status": "error",
        "dataset_version": None,
        "items": [],
        "error_code": error_code,
    }


def create_app(
    settings: Settings | None = None,
    *,
    store: RagStore | None = None,
    embedder: Any = None,
    commerce: CommerceStore | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configured = settings or Settings.from_env()
        app.state.rag_settings = configured
        app.state.rag_store = store or RagStore(configured.rag_database_url)
        app.state.commerce_store = commerce
        try:
            type_registry(configured.product_type_registry_path)
            if commerce is None and configured.commerce_database_url:
                app.state.commerce_store = CommerceStore(configured)
            app.state.rag_embedder = embedder or create_embedder(configured)
            yield
        finally:
            if commerce is None and app.state.commerce_store is not None:
                app.state.commerce_store.close()
            if store is None:
                app.state.rag_store.close()

    app = FastAPI(
        title="Product RAG",
        version="0.4.0",
        description="Source-grounded hybrid retrieval and product-scoped review analysis.",
        lifespan=lifespan,
    )

    def pinned_test_items_run(request: Request) -> tuple[dict[str, Any] | None, str | None]:
        profile_name = "all_products"  # legacy catalog stays pinned independently
        active = request.app.state.rag_store.active_run(profile_name)
        if active is None:
            return None, "index_not_ready"
        if active["dataset_version"] != TEST_ITEMS_DATASET_VERSION:
            return None, "dataset_mismatch"
        categories = request.app.state.rag_store.supported_categories(active["run_id"])
        if categories != [TEST_ITEMS_CATEGORY]:
            return None, "dataset_mismatch"
        return active, None

    @app.get("/healthz")
    async def healthz(request: Request) -> dict[str, Any]:
        profile_name = request.app.state.rag_settings.default_profile
        uses_bge = request.app.state.rag_settings.embedding_model == BGE_M3_MODEL
        try:
            active = request.app.state.rag_store.active_run(profile_name)
            category_reader = getattr(
                request.app.state.rag_store, "supported_categories", None
            )
            supported = (
                category_reader(active["run_id"])
                if active is not None and callable(category_reader)
                else []
            )
            bge_ready = active is not None and bge_profile_ready(request.app.state.rag_store, active) if uses_bge else False
        except psycopg.Error:
            return {
                "status": "error",
                "profile_name": profile_name,
                "error_code": "database_failed",
            }
        if active is None:
            return {
                "status": "not_ready",
                "profile_name": profile_name,
                "dataset_version": None,
                "supported_categories": [],
            }
        if uses_bge and not bge_ready:
            return {
                "status": "not_ready", "profile_name": profile_name,
                "error_code": "index_not_ready", "dataset_version": active["dataset_version"],
                "supported_categories": supported,
            }
        if not uses_bge and active["embedding_model"] != request.app.state.rag_settings.embedding_model:
            return {
                "status": "not_ready",
                "profile_name": profile_name,
                "error_code": "configuration_error",
                "dataset_version": active["dataset_version"],
                "supported_categories": supported,
            }
        return {
            "status": "ok",
            "profile_name": profile_name,
            "dataset_version": active["dataset_version"],
            "supported_categories": supported,
            "allowed_profiles": list(request.app.state.rag_settings.allowed_profiles),
            "commerce_configured": request.app.state.commerce_store is not None,
            "embedding_model": request.app.state.rag_settings.embedding_model,
            "embedding_dimension": 1024 if uses_bge else 384,
        }

    @app.post("/v1/rag/search")
    async def search(request: Request) -> JSONResponse:
        started = time.perf_counter()
        request_id: str | None = None
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > MAX_REQUEST_BYTES:
                    response = _error_response(None, "invalid_request")
                    return JSONResponse(response, status_code=422)
            except ValueError:
                response = _error_response(None, "invalid_request")
                return JSONResponse(response, status_code=422)
        raw = await request.body()
        if len(raw) > MAX_REQUEST_BYTES:
            response = _error_response(None, "invalid_request")
            return JSONResponse(response, status_code=422)
        try:
            payload = json.loads(raw)
            if isinstance(payload, dict):
                request_id = _safe_request_id(payload.get("request_id"))
            parsed = RagSearchRequest.model_validate(payload)
        except (json.JSONDecodeError, UnicodeError, ValidationError, ValueError, TypeError):
            response = _error_response(request_id, "invalid_request")
            logger.info(
                "rag_search request_id=%s status=error error_code=invalid_request",
                request_id,
            )
            return JSONResponse(response, status_code=422)

        try:
            response = await run_in_threadpool(hybrid_search,
                request.app.state.rag_store,
                request.app.state.rag_embedder,
                request.app.state.rag_settings,
                parsed,
                commerce=request.app.state.commerce_store,
            )
            status_code = _status_code(response["error_code"]) if response["status"] == "error" else 200
        except SearchError as error:
            code = error.code if error.code in {"embedding_failed", "search_failed"} else "search_failed"
            response = _error_response(request_id, code)
            status_code = _status_code(code)
        except psycopg.Error as error:
            logger.warning(
                "rag_search request_id=%s status=error error_code=database_failed "
                "exception=%s sqlstate=%s",
                request_id,
                type(error).__name__,
                getattr(error, "sqlstate", None),
            )
            response = _error_response(request_id, "database_failed")
            status_code = _status_code("database_failed")
        except TimeoutError:
            response = _error_response(request_id, "timeout")
            status_code = _status_code("timeout")
        except Exception:
            response = _error_response(request_id, "search_failed")
            status_code = _status_code("search_failed")

        elapsed_ms = round((time.perf_counter() - started) * 1000)
        logger.info(
            "rag_search request_id=%s status=%s elapsed_ms=%d error_code=%s",
            request_id,
            response["status"],
            elapsed_ms,
            response["error_code"],
        )
        return JSONResponse(response, status_code=status_code)

    @app.post("/v1/rag/reviews/search")
    async def search_reviews(request: Request) -> JSONResponse:
        request_id: str | None = None
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > MAX_REQUEST_BYTES:
                    return JSONResponse(_review_error_response(None, "invalid_request"), status_code=422)
            except ValueError:
                return JSONResponse(_review_error_response(None, "invalid_request"), status_code=422)
        raw = await request.body()
        if len(raw) > MAX_REQUEST_BYTES:
            return JSONResponse(_review_error_response(None, "invalid_request"), status_code=422)
        try:
            payload = json.loads(raw)
            if isinstance(payload, dict):
                request_id = _safe_request_id(payload.get("request_id"))
            parsed = ProductScopedReviewRequest.model_validate(payload)
        except (json.JSONDecodeError, UnicodeError, ValidationError, ValueError, TypeError):
            return JSONResponse(_review_error_response(request_id, "invalid_request"), status_code=422)
        try:
            response = await run_in_threadpool(
                search_product_reviews,
                request.app.state.rag_store,
                request.app.state.rag_embedder,
                request.app.state.rag_settings,
                parsed,
            )
            return JSONResponse(response)
        except ReviewFeatureError as error:
            code = error.code if error.code in {
                "unsupported_profile", "unsupported_category", "unsupported_aspect",
                "unknown_product_id", "ambiguous_product_id", "dataset_version_mismatch",
                "index_not_ready", "configuration_error", "embedding_failed",
            } else "search_failed"
            return JSONResponse(_review_error_response(request_id, code), status_code=_review_status_code(code))
        except psycopg.Error as error:
            logger.warning(
                "rag_review_search request_id=%s status=error error_code=database_failed "
                "exception=%s sqlstate=%s",
                request_id,
                type(error).__name__,
                getattr(error, "sqlstate", None),
            )
            return JSONResponse(_review_error_response(request_id, "database_failed"), status_code=503)
        except TimeoutError:
            return JSONResponse(_review_error_response(request_id, "timeout"), status_code=504)
        except Exception:
            return JSONResponse(_review_error_response(request_id, "search_failed"), status_code=500)

    @app.post("/v1/rag/reviews/aspect-aggregate")
    async def aggregate_reviews(request: Request) -> JSONResponse:
        request_id: str | None = None
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > MAX_REQUEST_BYTES:
                    return JSONResponse(_review_error_response(None, "invalid_request"), status_code=422)
            except ValueError:
                return JSONResponse(_review_error_response(None, "invalid_request"), status_code=422)
        raw = await request.body()
        if len(raw) > MAX_REQUEST_BYTES:
            return JSONResponse(_review_error_response(None, "invalid_request"), status_code=422)
        try:
            payload = json.loads(raw)
            if isinstance(payload, dict):
                request_id = _safe_request_id(payload.get("request_id"))
            parsed = ProductScopedReviewAggregateRequest.model_validate(payload)
        except (json.JSONDecodeError, UnicodeError, ValidationError, ValueError, TypeError):
            return JSONResponse(_review_error_response(request_id, "invalid_request"), status_code=422)
        try:
            response = await run_in_threadpool(
                aggregate_product_reviews,
                request.app.state.rag_store,
                request.app.state.rag_settings,
                parsed,
            )
            return JSONResponse(response)
        except ReviewFeatureError as error:
            code = error.code if error.code in {
                "unsupported_profile", "unsupported_category", "unsupported_aspect",
                "unknown_product_id", "ambiguous_product_id", "dataset_version_mismatch",
                "index_not_ready",
            } else "search_failed"
            return JSONResponse(_review_error_response(request_id, code), status_code=_review_status_code(code))
        except psycopg.errors.UndefinedTable:
            return JSONResponse(
                _review_error_response(request_id, "annotation_schema_not_ready"),
                status_code=503,
            )
        except psycopg.Error as error:
            logger.warning(
                "rag_review_aggregate request_id=%s status=error error_code=database_failed "
                "exception=%s sqlstate=%s",
                request_id,
                type(error).__name__,
                getattr(error, "sqlstate", None),
            )
            return JSONResponse(_review_error_response(request_id, "database_failed"), status_code=503)
        except TimeoutError:
            return JSONResponse(_review_error_response(request_id, "timeout"), status_code=504)
        except Exception:
            return JSONResponse(_review_error_response(request_id, "search_failed"), status_code=500)

    @app.get("/v1/catalog/test-items")
    async def list_test_items(request: Request) -> JSONResponse:
        try:
            active, pinned_error = pinned_test_items_run(request)
            if pinned_error:
                return JSONResponse(
                    {"status": "error", "error_code": pinned_error},
                    status_code=503,
                )
            raw_limit = request.query_params.get("limit", "50")
            raw_cursor = request.query_params.get("cursor", "0")
            try:
                limit = int(raw_limit)
                offset = int(raw_cursor)
            except ValueError:
                return JSONResponse(
                    {"status": "error", "error_code": "invalid_request"},
                    status_code=422,
                )
            if not 1 <= limit <= 50 or not 0 <= offset <= 10000:
                return JSONResponse(
                    {"status": "error", "error_code": "invalid_request"},
                    status_code=422,
                )

            assert active is not None
            rows, total = request.app.state.rag_store.list_test_items(
                active["run_id"], TEST_ITEMS_DATASET_VERSION, limit, offset
            )
            items: list[dict[str, Any]] = []
            for row in rows:
                payload = row["product_payload"]
                if (
                    not isinstance(payload, dict)
                    or payload.get("source_dataset") != "test_items"
                    or payload.get("category") != TEST_ITEMS_CATEGORY
                    or not isinstance(payload.get("title"), str)
                    or not isinstance(payload.get("brand"), str)
                    or not isinstance(payload.get("description"), str)
                    or not isinstance(payload.get("price"), dict)
                    or payload["price"].get("is_simulated") is not True
                    or not isinstance(payload.get("stock_qty"), int)
                ):
                    return JSONResponse(
                        {"status": "error", "error_code": "dataset_mismatch"},
                        status_code=503,
                    )
                image_urls = payload.get("image_urls")
                features = payload.get("features")
                items.append({
                    "product_id": row["product_id"],
                    "category": TEST_ITEMS_CATEGORY,
                    "title": payload["title"],
                    "brand": payload["brand"],
                    "description": payload["description"],
                    "image_urls": [x for x in image_urls if isinstance(x, str)]
                    if isinstance(image_urls, list) else [],
                    "features": features if isinstance(features, dict) else {},
                    "price": {
                        "amount_won": int(row["price_amount"]),
                        "currency": row["price_currency"],
                        "is_simulated": True,
                    },
                    "stock_qty": payload["stock_qty"],
                    "rating_summary": {
                        "avg": row["rating_avg"],
                        "count": row["review_count"],
                    },
                })

            next_offset = offset + len(items)
            has_more = next_offset < total
            return JSONResponse({
                "status": "ok",
                "profile_name": "all_products",
                "dataset_version": TEST_ITEMS_DATASET_VERSION,
                "category": TEST_ITEMS_CATEGORY,
                "total": total,
                "items": items,
                "next_cursor": str(next_offset) if has_more else None,
                "has_more": has_more,
            })
        except psycopg.Error as error:
            logger.warning(
                "test_items_catalog status=error error_code=database_failed exception=%s sqlstate=%s",
                type(error).__name__,
                getattr(error, "sqlstate", None),
            )
            return JSONResponse(
                {"status": "error", "error_code": "database_failed"},
                status_code=503,
            )
        except (TypeError, ValueError):
            return JSONResponse(
                {"status": "error", "error_code": "dataset_mismatch"},
                status_code=503,
            )

    @app.get("/v1/catalog/test-items/{product_id}/reviews")
    async def test_item_reviews(product_id: str, request: Request) -> JSONResponse:
        try:
            active, pinned_error = pinned_test_items_run(request)
            if pinned_error:
                return JSONResponse({"status": "error", "error_code": pinned_error}, status_code=503)
            assert active is not None
            chunks = request.app.state.rag_store.test_item_review_chunks(
                active["run_id"], TEST_ITEMS_DATASET_VERSION, product_id
            )
            reviews: dict[str, dict[str, Any]] = {}
            for chunk in chunks:
                metadata = chunk["source_metadata"]
                if (
                    metadata.get("source_dataset") != "test_items"
                    or metadata.get("source_kind") not in ("REAL", "SYNTHETIC")
                    or type(metadata.get("rating")) is not int
                    or not 1 <= metadata["rating"] <= 5
                    or not isinstance(metadata.get("timestamp"), str)
                ):
                    raise ValueError("invalid_review_metadata")
                source_id = chunk["source_id"]
                if source_id not in reviews:
                    review_id = hashlib.sha256(source_id.encode()).hexdigest()
                    reviews[source_id] = {
                        "id": review_id, "product_id": product_id, "variant_id": None,
                        "rating": metadata["rating"], "body": "",
                        "source_kind": metadata["source_kind"],
                        "source_ref": f"test_items:{review_id}",
                        "written_at": metadata["timestamp"],
                    }
                review = reviews[source_id]
                start, end = chunk["start_offset"], chunk["end_offset"]
                text = chunk["evidence_text"]
                body = review["body"]
                if start > len(body) or end - start != len(text):
                    raise ValueError("incomplete_review_chunks")
                overlap = min(len(body), end) - start
                if body[start:start + overlap] != text[:overlap]:
                    raise ValueError("inconsistent_review_chunks")
                if end > len(body):
                    review["body"] += text[len(body) - start:]
            return JSONResponse({
                "status": "ok", "dataset_version": TEST_ITEMS_DATASET_VERSION,
                "reviews": list(reviews.values()),
            })
        except psycopg.Error:
            return JSONResponse({"status": "error", "error_code": "database_failed"}, status_code=503)
        except (TypeError, ValueError, KeyError):
            return JSONResponse({"status": "error", "error_code": "dataset_mismatch"}, status_code=503)

    return app


app = create_app()
