"""Resume-safe BGE-M3 embedding of evidence chunks already stored in Postgres."""

from __future__ import annotations

import os
import resource
import sys
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any

from psycopg import ProgrammingError
from psycopg.conninfo import conninfo_to_dict

from .bge_m3 import BGE_M3_MODEL, BGE_M3_MODEL_REVISION


FULL_RUN_ID = "e925490f-4f34-4c03-9248-eb9ebdfcde48"
FULL_DATASET_VERSION = (
    "test_items2:v6.1-review-refined:sha256=94681a28271ca9b1:"
    "products=1500:reviews=46100"
)
FULL_CATEGORY_CHUNK_COUNTS = {
    "beauty": 78_595,
    "fashion": 11_566,
    "food": 13_409,
    "living": 10_536,
}
FULL_CHUNK_COUNT = 114_106


@dataclass(frozen=True)
class EmbeddingIndexSummary:
    run_id: str
    dataset_version: str
    category: str
    embedding_model: str
    model_revision: str
    total_chunk_count: int
    preexisting_vector_count: int
    embedded_chunk_count: int
    document_embedding_seconds: float
    elapsed_seconds: float
    chunks_per_second: float
    model_load_seconds: float
    cpu_thread_count: int | None
    max_rss_mb: float
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def comparison_database_target(database_url: str) -> tuple[str | None, int | None, str]:
    try:
        options = conninfo_to_dict(database_url)
        port = int(options.get("port", ""))
    except (ProgrammingError, TypeError, ValueError):
        raise ValueError("comparison_database_target_mismatch")
    hostname = options.get("host")
    hostaddr = options.get("hostaddr") or os.getenv("PGHOSTADDR")
    database_name = options.get("dbname")
    if (
        hostname != "127.0.0.1"
        or (hostaddr is not None and hostaddr != "127.0.0.1")
        or options.get("service") is not None
        or options.get("servicefile") is not None
        or os.getenv("PGSERVICE") is not None
        or os.getenv("PGSERVICEFILE") is not None
        or port != 5432
        or database_name != "toss_rag"
    ):
        raise ValueError("comparison_database_target_mismatch")
    return hostname, port, database_name


def _max_rss_mb() -> float:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    megabytes = peak / (1024 * 1024) if sys.platform == "darwin" else peak / 1024
    return round(float(megabytes), 2)


def validate_full_dataset_target(
    store: Any, *, run_id: str, dataset_version: str
) -> int:
    """Fail closed unless the approved complete test_items2 snapshot is present."""
    if run_id != FULL_RUN_ID or dataset_version != FULL_DATASET_VERSION:
        raise ValueError("embedding_target_mismatch")
    active_run_reader = getattr(store, "active_run", None)
    active_run = active_run_reader() if callable(active_run_reader) else None
    if (
        active_run is None
        or str(active_run.get("run_id")) != run_id
        or active_run.get("dataset_version") != dataset_version
    ):
        raise ValueError("embedding_target_mismatch")
    category_counts = store.embedding_target_category_counts(run_id, dataset_version)
    if category_counts != FULL_CATEGORY_CHUNK_COUNTS:
        raise ValueError("embedding_target_mismatch")
    total_chunk_count = store.embedding_target_chunk_count(
        run_id, dataset_version, "*"
    )
    if total_chunk_count != FULL_CHUNK_COUNT or sum(category_counts.values()) != FULL_CHUNK_COUNT:
        raise ValueError("embedding_target_mismatch")
    return total_chunk_count


def index_existing_chunks(
    store: Any,
    embedder: Any,
    *,
    run_id: str,
    dataset_version: str,
    category: str,
    batch_size: int = 16,
    model_load_seconds: float = 0.0,
) -> EmbeddingIndexSummary:
    if batch_size < 1 or batch_size > 16:
        raise ValueError("invalid_embedding_batch_size")
    if getattr(embedder, "dimension", None) != 1024:
        raise ValueError("embedding_dimension_mismatch")
    if getattr(embedder, "max_length", None) != 128:
        raise ValueError("embedding_input_length_mismatch")

    # Resolve the exact run and category before creating a profile or invoking the model.
    if category == "*":
        total_chunk_count = validate_full_dataset_target(
            store, run_id=run_id, dataset_version=dataset_version
        )
    else:
        total_chunk_count = store.embedding_target_chunk_count(
            run_id, dataset_version, category
        )
    embedding_model = getattr(embedder, "model_name", None)
    model_revision = getattr(embedder, "model_revision", None)
    if not embedding_model or not model_revision:
        raise ValueError("embedding_model_metadata_missing")
    if category == "*" and (
        embedding_model != BGE_M3_MODEL
        or model_revision != BGE_M3_MODEL_REVISION
        or getattr(embedder, "dimension", None) != 1024
        or getattr(embedder, "max_length", None) != 128
    ):
        raise ValueError("embedding_model_configuration_mismatch")

    started = perf_counter()
    document_embedding_seconds = 0.0
    embedded_chunk_count = 0
    preexisting_vector_count = 0
    profile_registered = False
    try:
        if category == "*":
            store.prepare_full_embedding_profile(
                run_id=run_id,
                embedding_model=embedding_model,
                model_revision=model_revision,
                expected_chunk_count=total_chunk_count,
            )
        else:
            store.register_embedding_profile(
                run_id=run_id,
                embedding_model=embedding_model,
                model_revision=model_revision,
                dimension=1024,
                max_input_tokens=128,
                category_scope=category,
                expected_chunk_count=total_chunk_count,
            )
        profile_registered = True
        _, preexisting_vector_count = store.embedding_profile_counts(
            run_id, embedding_model, category
        )

        while True:
            missing = store.missing_embedding_texts(
                run_id, embedding_model, category, batch_size
            )
            if not missing:
                break
            if len(missing) > batch_size:
                raise ValueError("embedding_batch_limit_exceeded")
            embedding_started = perf_counter()
            vectors = embedder.embed_documents([text for _, text in missing])
            document_embedding_seconds += perf_counter() - embedding_started
            if len(vectors) != len(missing):
                raise ValueError("embedding_count_mismatch")
            if any(len(vector) != 1024 for vector in vectors):
                raise ValueError("embedding_dimension_mismatch")
            store.upsert_embedding_vectors(
                run_id,
                embedding_model,
                tuple(
                    (chunk_id, vector)
                    for (chunk_id, _), vector in zip(missing, vectors, strict=True)
                ),
            )
            embedded_chunk_count += len(missing)

        expected_count, stored_count = store.embedding_profile_counts(
            run_id, embedding_model, category
        )
        if expected_count != total_chunk_count or stored_count != total_chunk_count:
            raise ValueError("embedding_profile_incomplete")
        store.mark_embedding_profile_ready(run_id, embedding_model, category)
    except BaseException:
        if profile_registered:
            try:
                store.mark_embedding_profile_failed(run_id, embedding_model)
            except Exception:
                pass
        raise

    elapsed_seconds = max(perf_counter() - started, 0.0)
    chunks_per_second = (
        embedded_chunk_count / document_embedding_seconds
        if document_embedding_seconds
        else 0.0
    )
    return EmbeddingIndexSummary(
        run_id=run_id,
        dataset_version=dataset_version,
        category=category,
        embedding_model=embedding_model,
        model_revision=model_revision,
        total_chunk_count=total_chunk_count,
        preexisting_vector_count=preexisting_vector_count,
        embedded_chunk_count=embedded_chunk_count,
        document_embedding_seconds=round(document_embedding_seconds, 6),
        elapsed_seconds=round(elapsed_seconds, 3),
        chunks_per_second=round(chunks_per_second, 3),
        model_load_seconds=round(max(float(model_load_seconds), 0.0), 3),
        cpu_thread_count=getattr(embedder, "cpu_thread_count", None),
        max_rss_mb=_max_rss_mb(),
        status="ready",
    )
