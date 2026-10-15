"""FastAPI boundary for the Agent-to-RAG v0.1 request/response contract."""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .config import Settings
from .embeddings import create_embedder
from .retriever import SearchError, hybrid_search
from .schemas import RagSearchRequest
from .store import RagStore

logger = logging.getLogger("toss_ads.rag")
MAX_REQUEST_BYTES = 64 * 1024


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
        "index_not_ready": 503,
        "embedding_failed": 503,
        "database_failed": 503,
        "configuration_error": 503,
        "timeout": 504,
    }.get(error_code, 500)


def create_app(
    settings: Settings | None = None,
    *,
    store: RagStore | None = None,
    embedder: Any = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configured = settings or Settings.from_env()
        app.state.rag_settings = configured
        app.state.rag_store = store or RagStore(configured.rag_database_url)
        try:
            app.state.rag_embedder = embedder or create_embedder(configured)
            yield
        finally:
            if store is None:
                app.state.rag_store.close()

    app = FastAPI(
        title="Amazon Reviews RAG",
        version="0.2.0",
        description="Source-grounded BM25 and vector retrieval for Amazon Reviews.",
        lifespan=lifespan,
    )

    @app.get("/healthz")
    async def healthz(request: Request) -> dict[str, Any]:
        try:
            active = request.app.state.rag_store.active_run()
            category_reader = getattr(
                request.app.state.rag_store, "supported_categories", None
            )
            supported = (
                category_reader(active["run_id"])
                if active is not None and callable(category_reader)
                else []
            )
        except psycopg.Error:
            return {"status": "error", "error_code": "database_failed"}
        if active is None:
            return {
                "status": "not_ready",
                "dataset_version": None,
                "supported_categories": [],
            }
        if active["embedding_model"] != request.app.state.rag_settings.embedding_model:
            return {
                "status": "not_ready",
                "error_code": "configuration_error",
                "supported_categories": supported,
            }
        return {
            "status": "ok",
            "dataset_version": active["dataset_version"],
            "supported_categories": supported,
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
            response = hybrid_search(
                request.app.state.rag_store,
                request.app.state.rag_embedder,
                request.app.state.rag_settings,
                parsed,
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

    return app


app = create_app()
