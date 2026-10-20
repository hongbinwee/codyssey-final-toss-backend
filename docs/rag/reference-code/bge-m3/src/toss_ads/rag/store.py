"""PostgreSQL persistence and channel-specific retrieval for RAG data."""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from psycopg.types.json import Jsonb

from .source import without_user_ids
from .types import EvidenceChunk, IndexedProduct, QuarantinedProduct


class RagStore:
    def __init__(self, database_url: str):
        if not database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("invalid_database_url")
        self.database_url = database_url
        self.pool = ConnectionPool(
            conninfo=database_url,
            min_size=1,
            max_size=8,
            kwargs={"row_factory": dict_row},
            open=True,
        )
        self.pool.wait(timeout=10)

    def close(self) -> None:
        self.pool.close()

    def __enter__(self) -> "RagStore":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def begin_index_run(
        self,
        dataset_version: str,
        embedding_model: str,
        chunker_version: str,
        category_policy_version: str,
    ) -> str:
        run_id = str(uuid.uuid4())
        with self.pool.connection() as connection:
            connection.execute(
                """INSERT INTO rag.index_runs
                       (run_id, dataset_version, embedding_model, chunker_version,
                        category_policy_version, status)
                   VALUES (%s, %s, %s, %s, %s, 'building')""",
                (run_id, dataset_version, embedding_model, chunker_version, category_policy_version),
            )
        return run_id

    def resume_index_run(
        self,
        run_id: str,
        dataset_version: str,
        embedding_model: str,
        chunker_version: str,
        category_policy_version: str,
    ) -> str:
        with self.pool.connection() as connection:
            row = connection.execute(
                """SELECT dataset_version, embedding_model, chunker_version,
                          category_policy_version, status
                   FROM rag.index_runs WHERE run_id = %s""",
                (run_id,),
            ).fetchone()
        if row is None or row["status"] != "building" or (
            row["dataset_version"],
            row["embedding_model"],
            row["chunker_version"],
            row["category_policy_version"],
        ) != (
            dataset_version,
            embedding_model,
            chunker_version,
            category_policy_version,
        ):
            raise ValueError("index_run_not_resumable")
        return run_id

    def missing_chunks(
        self, run_id: str, chunks: Sequence[EvidenceChunk]
    ) -> tuple[EvidenceChunk, ...]:
        if not chunks:
            return ()
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        with self.pool.connection() as connection:
            rows = connection.execute(
                """SELECT chunk_id FROM rag.evidence_chunks
                   WHERE run_id = %s AND chunk_id = ANY(%s)""",
                (run_id, chunk_ids),
            ).fetchall()
        existing_ids = {row["chunk_id"] for row in rows}
        return tuple(chunk for chunk in chunks if chunk.chunk_id not in existing_ids)

    def upsert_products(self, run_id: str, products: Sequence[IndexedProduct]) -> None:
        if not products:
            return
        rows = [
            (
                run_id,
                product.dataset_version,
                product.category,
                product.product_id,
                Jsonb(without_user_ids(product.product_payload)),
                product.price_amount,
                product.price_currency,
            )
            for product in products
        ]
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.executemany(
                    """INSERT INTO rag.indexed_products
                           (run_id, dataset_version, category, product_id,
                            product_payload, price_amount, price_currency)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (run_id, category, product_id) DO UPDATE SET
                           dataset_version = EXCLUDED.dataset_version,
                           product_payload = EXCLUDED.product_payload,
                           price_amount = EXCLUDED.price_amount,
                           price_currency = EXCLUDED.price_currency""",
                    rows,
                )

    def record_quarantined_products(
        self, run_id: str, products: Sequence[QuarantinedProduct]
    ) -> None:
        if not products:
            return
        rows = [
            (
                run_id,
                product.dataset_version,
                product.category,
                product.product_id,
                product.reason_code,
                product.policy_version,
                product.product_title,
                product.main_category,
                Jsonb(list(product.categories)),
                Jsonb(list(product.type_signals)),
            )
            for product in products
        ]
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.executemany(
                    """INSERT INTO rag.quarantined_products
                           (run_id, dataset_version, category, product_id,
                            reason_code, policy_version, product_title, main_category,
                            categories, type_signals, review_status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending_review')
                       ON CONFLICT (run_id, category, product_id) DO UPDATE SET
                           dataset_version = EXCLUDED.dataset_version,
                           reason_code = EXCLUDED.reason_code,
                           policy_version = EXCLUDED.policy_version,
                           product_title = EXCLUDED.product_title,
                           main_category = EXCLUDED.main_category,
                           categories = EXCLUDED.categories,
                           type_signals = EXCLUDED.type_signals,
                           review_status = 'pending_review'""",
                    rows,
                )

    def upsert_chunks(
        self,
        run_id: str,
        chunks_and_vectors: Sequence[tuple[EvidenceChunk, Sequence[float]]],
    ) -> None:
        if not chunks_and_vectors:
            return
        rows = []
        for chunk, vector in chunks_and_vectors:
            if len(vector) != 384:
                raise ValueError("embedding_dimension_mismatch")
            chunk_key = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{run_id}:{chunk.chunk_id}"))
            rows.append(
                (
                    run_id,
                    chunk_key,
                    chunk.chunk_id,
                    chunk.dataset_version,
                    chunk.category,
                    chunk.product_id,
                    chunk.source_type,
                    chunk.source_id,
                    chunk.source_field,
                    chunk.start_offset,
                    chunk.end_offset,
                    chunk.evidence_text,
                    chunk.embedding_text,
                    Jsonb(without_user_ids(chunk.source_metadata)),
                    json.dumps([float(value) for value in vector], separators=(",", ":")),
                    chunk.embedding_model,
                    chunk.chunker_version,
                )
            )
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.executemany(
                    """INSERT INTO rag.evidence_chunks
                           (run_id, chunk_key, chunk_id, dataset_version, category,
                            product_id, source_type, source_id, source_field,
                            start_offset, end_offset, evidence_text, embedding_text,
                            source_metadata, embedding, embedding_model, chunker_version)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                               %s::vector, %s, %s)
                       ON CONFLICT (run_id, chunk_id) DO UPDATE SET
                           chunk_key = EXCLUDED.chunk_key,
                           dataset_version = EXCLUDED.dataset_version,
                           category = EXCLUDED.category,
                           product_id = EXCLUDED.product_id,
                           source_type = EXCLUDED.source_type,
                           source_id = EXCLUDED.source_id,
                           source_field = EXCLUDED.source_field,
                           start_offset = EXCLUDED.start_offset,
                           end_offset = EXCLUDED.end_offset,
                           evidence_text = EXCLUDED.evidence_text,
                           embedding_text = EXCLUDED.embedding_text,
                           source_metadata = EXCLUDED.source_metadata,
                           embedding = EXCLUDED.embedding,
                           embedding_model = EXCLUDED.embedding_model,
                           chunker_version = EXCLUDED.chunker_version""",
                    rows,
                )

    def activate_dataset(self, run_id: str, counts: dict[str, Any]) -> None:
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE rag.index_runs SET status = 'superseded'
                       WHERE status = 'active'"""
                )
                cursor.execute(
                    """UPDATE rag.index_runs
                       SET status = 'active', counts = %s, completed_at = now(), error_code = NULL
                       WHERE run_id = %s AND status = 'building'""",
                    (Jsonb(counts), run_id),
                )
                if cursor.rowcount != 1:
                    raise ValueError("index_run_not_building")

    def fail_index_run(self, run_id: str, error_code: str, counts: dict[str, Any]) -> None:
        safe_codes = {
            "source_failed",
            "source_version_changed",
            "source_count_mismatch",
            "database_failed",
            "embedding_failed",
            "invalid_source_linkage",
            "index_failed",
        }
        if error_code not in safe_codes:
            error_code = "index_failed"
        with self.pool.connection() as connection:
            connection.execute(
                """UPDATE rag.index_runs
                   SET status = 'failed', counts = %s, error_code = %s, completed_at = now()
                   WHERE run_id = %s AND status = 'building'""",
                (Jsonb(counts), error_code, run_id),
            )

    def active_run(self) -> dict[str, Any] | None:
        with self.pool.connection() as connection:
            return connection.execute(
                """SELECT run_id::text AS run_id, dataset_version,
                          embedding_model, chunker_version
                   FROM rag.index_runs WHERE status = 'active'
                   ORDER BY completed_at DESC, started_at DESC, run_id DESC
                   LIMIT 1"""
            ).fetchone()

    def supported_categories(self, run_id: str) -> list[str]:
        with self.pool.connection() as connection:
            row = connection.execute(
                """SELECT COALESCE(array_agg(category ORDER BY category), ARRAY[]::text[])
                   AS categories
                   FROM (
                       SELECT DISTINCT category
                       FROM rag.indexed_products
                       WHERE run_id = %s
                   ) AS active_categories""",
                (run_id,),
            ).fetchone()
        return list(row["categories"] or [])

    def search_bm25(
        self,
        run_id: str,
        query: str,
        limit: int,
        category: str | None = None,
        source_type: str | None = None,
    ) -> list[dict[str, Any]]:
        with self.pool.connection() as connection:
            rows = connection.execute(
                """SELECT c.chunk_id, c.category, c.product_id, c.source_type,
                          c.source_id, c.source_field, c.start_offset, c.end_offset,
                          c.evidence_text, c.source_metadata, p.product_payload,
                          pdb.score(c.chunk_key) AS score
                   FROM rag.evidence_chunks AS c
                   JOIN rag.indexed_products AS p
                     ON p.run_id = c.run_id AND p.category = c.category
                    AND p.product_id = c.product_id
                   WHERE c.run_id = %s
                     AND (%s::text IS NULL OR c.category = %s)
                     AND (%s::text IS NULL OR c.source_type = %s)
                     AND c.embedding_text ||| %s
                   ORDER BY score DESC, c.chunk_id ASC
                   LIMIT %s""",
                (run_id, category, category, source_type, source_type, query, limit),
                prepare=False,
            ).fetchall()
        return list(rows)

    def register_embedding_profile(
        self,
        *,
        run_id: str,
        embedding_model: str,
        model_revision: str,
        dimension: int,
        max_input_tokens: int,
        category_scope: str,
        expected_chunk_count: int,
    ) -> None:
        if dimension != 1024:
            raise ValueError("embedding_dimension_mismatch")
        if not model_revision or not category_scope or max_input_tokens <= 0 or expected_chunk_count < 0:
            raise ValueError("invalid_embedding_profile")

        with self.pool.connection() as connection:
            connection.execute(
                """INSERT INTO rag.index_run_embedding_profiles
                       (run_id, embedding_model, model_revision, dimension,
                        max_input_tokens, category_scope, status, chunk_count)
                   VALUES (%s, %s, %s, %s, %s, %s, 'building', %s)
                   ON CONFLICT (run_id, embedding_model) DO NOTHING""",
                (
                    run_id,
                    embedding_model,
                    model_revision,
                    dimension,
                    max_input_tokens,
                    category_scope,
                    expected_chunk_count,
                ),
            )
            profile = connection.execute(
                """SELECT model_revision, dimension, max_input_tokens,
                          category_scope, chunk_count, status
                   FROM rag.index_run_embedding_profiles
                   WHERE run_id = %s AND embedding_model = %s""",
                (run_id, embedding_model),
            ).fetchone()
            if profile is None or (
                profile["model_revision"],
                profile["dimension"],
                profile["max_input_tokens"],
                profile["category_scope"],
                profile["chunk_count"],
            ) != (
                model_revision,
                dimension,
                max_input_tokens,
                category_scope,
                expected_chunk_count,
            ):
                raise ValueError("embedding_profile_conflict")
            if profile["status"] == "failed":
                connection.execute(
                    """UPDATE rag.index_run_embedding_profiles
                       SET status = 'building'
                       WHERE run_id = %s AND embedding_model = %s AND status = 'failed'""",
                    (run_id, embedding_model),
                )

    def prepare_full_embedding_profile(
        self,
        *,
        run_id: str,
        embedding_model: str,
        model_revision: str,
        expected_chunk_count: int,
    ) -> None:
        if not model_revision or expected_chunk_count <= 0:
            raise ValueError("invalid_embedding_profile")

        with self.pool.connection() as connection:
            active_run = connection.execute(
                """SELECT run_id::text AS run_id
                   FROM rag.index_runs
                   WHERE status = 'active'
                   ORDER BY completed_at DESC, started_at DESC, run_id DESC
                   LIMIT 1
                   FOR UPDATE"""
            ).fetchone()
            if active_run is None or active_run["run_id"] != run_id:
                raise ValueError("embedding_target_mismatch")

            target = connection.execute(
                """SELECT COUNT(*)::bigint AS target_chunk_count
                   FROM rag.evidence_chunks
                   WHERE run_id = %s""",
                (run_id,),
            ).fetchone()
            if target is None or int(target["target_chunk_count"]) != expected_chunk_count:
                raise ValueError("embedding_target_mismatch")

            profile = connection.execute(
                """SELECT model_revision, dimension, max_input_tokens,
                          category_scope, chunk_count, status
                   FROM rag.index_run_embedding_profiles
                   WHERE run_id = %s AND embedding_model = %s
                   FOR UPDATE""",
                (run_id, embedding_model),
            ).fetchone()
            if profile is None or (
                profile["model_revision"],
                profile["dimension"],
                profile["max_input_tokens"],
            ) != (model_revision, 1024, 128):
                raise ValueError("embedding_profile_conflict")

            if profile["category_scope"] == "beauty":
                counts = connection.execute(
                    """SELECT COUNT(c.chunk_id)::bigint AS expected_chunk_count,
                              COUNT(e.chunk_id)::bigint AS stored_vector_count
                       FROM rag.evidence_chunks AS c
                       LEFT JOIN rag.evidence_chunk_embeddings AS e
                         ON e.run_id = c.run_id AND e.chunk_id = c.chunk_id
                        AND e.embedding_model = %s
                       WHERE c.run_id = %s AND c.category = 'beauty'""",
                    (embedding_model, run_id),
                ).fetchone()
                if (
                    counts is None
                    or profile["chunk_count"] != int(counts["expected_chunk_count"])
                    or int(counts["expected_chunk_count"])
                    != int(counts["stored_vector_count"])
                ):
                    raise ValueError("embedding_profile_incomplete")
                connection.execute(
                    """UPDATE rag.index_run_embedding_profiles
                       SET category_scope = '*', chunk_count = %s,
                           status = 'building', updated_at = now()
                       WHERE run_id = %s AND embedding_model = %s""",
                    (expected_chunk_count, run_id, embedding_model),
                )
                return

            if profile["category_scope"] != "*" or profile["chunk_count"] != expected_chunk_count:
                raise ValueError("embedding_profile_conflict")
            if profile["status"] == "failed":
                connection.execute(
                    """UPDATE rag.index_run_embedding_profiles
                       SET status = 'building', updated_at = now()
                       WHERE run_id = %s AND embedding_model = %s
                         AND category_scope = '*' AND status = 'failed'""",
                    (run_id, embedding_model),
                )

    def embedding_profile_info(
        self, run_id: str, embedding_model: str
    ) -> dict[str, Any] | None:
        with self.pool.connection() as connection:
            row = connection.execute(
                """SELECT model_revision, dimension, max_input_tokens,
                          category_scope, chunk_count, status
                   FROM rag.index_run_embedding_profiles
                   WHERE run_id = %s AND embedding_model = %s""",
                (run_id, embedding_model),
            ).fetchone()
        return dict(row) if row is not None else None

    def missing_embedding_texts(
        self, run_id: str, embedding_model: str, category: str, limit: int
    ) -> tuple[tuple[str, str], ...]:
        if limit <= 0:
            raise ValueError("invalid_embedding_batch_size")
        with self.pool.connection() as connection:
            rows = connection.execute(
                """SELECT c.chunk_id, c.embedding_text
                   FROM rag.evidence_chunks AS c
                   JOIN rag.index_run_embedding_profiles AS p
                     ON p.run_id = c.run_id AND p.embedding_model = %s
                    AND (p.category_scope = '*' OR p.category_scope = c.category)
                   LEFT JOIN rag.evidence_chunk_embeddings AS e
                     ON e.run_id = c.run_id AND e.chunk_id = c.chunk_id
                    AND e.embedding_model = %s
                   WHERE c.run_id = %s
                     AND (%s::text = '*' OR c.category = %s)
                     AND e.chunk_id IS NULL
                   ORDER BY c.chunk_id
                   LIMIT %s""",
                (
                    embedding_model,
                    embedding_model,
                    run_id,
                    category,
                    category,
                    limit,
                ),
            ).fetchall()
        return tuple((row["chunk_id"], row["embedding_text"]) for row in rows)

    def upsert_embedding_vectors(
        self,
        run_id: str,
        embedding_model: str,
        rows: Sequence[tuple[str, Sequence[float]]],
    ) -> None:
        if not rows:
            return
        chunk_ids = [chunk_id for chunk_id, _vector in rows]
        if len(set(chunk_ids)) != len(chunk_ids):
            raise ValueError("invalid_embedding_batch")
        prepared = []
        for chunk_id, vector in rows:
            if len(vector) != 1024:
                raise ValueError("embedding_dimension_mismatch")
            prepared.append(
                (
                    run_id,
                    chunk_id,
                    embedding_model,
                    json.dumps([float(value) for value in vector], separators=(",", ":")),
                )
            )
        with self.pool.connection() as connection:
            scope = connection.execute(
                """SELECT COUNT(DISTINCT c.chunk_id)::bigint AS allowed_chunk_count
                   FROM rag.index_run_embedding_profiles AS p
                   JOIN rag.evidence_chunks AS c ON c.run_id = p.run_id
                   WHERE p.run_id = %s AND p.embedding_model = %s
                     AND p.status = 'building'
                     AND (p.category_scope = '*' OR p.category_scope = c.category)
                     AND c.chunk_id = ANY(%s::text[])""",
                (run_id, embedding_model, chunk_ids),
            ).fetchone()
            if scope is None or int(scope["allowed_chunk_count"]) != len(chunk_ids):
                raise ValueError("embedding_target_mismatch")
            with connection.cursor() as cursor:
                cursor.executemany(
                    """INSERT INTO rag.evidence_chunk_embeddings
                           (run_id, chunk_id, embedding_model, embedding)
                       VALUES (%s, %s, %s, %s::vector)
                       ON CONFLICT (run_id, chunk_id, embedding_model) DO UPDATE SET
                           embedding = EXCLUDED.embedding,
                           updated_at = now()""",
                    prepared,
                )

    def embedding_profile_counts(
        self, run_id: str, embedding_model: str, category: str
    ) -> tuple[int, int]:
        with self.pool.connection() as connection:
            row = connection.execute(
                """SELECT CASE WHEN %s = '*'
                                THEN p.chunk_count
                                ELSE COUNT(c.chunk_id)::bigint
                           END AS expected_chunk_count,
                          COUNT(e.chunk_id)::bigint AS stored_vector_count
                   FROM rag.index_run_embedding_profiles AS p
                   LEFT JOIN rag.evidence_chunks AS c
                     ON c.run_id = p.run_id
                    AND (p.category_scope = '*' OR c.category = p.category_scope)
                    AND (%s::text = '*' OR c.category = %s)
                   LEFT JOIN rag.evidence_chunk_embeddings AS e
                     ON e.run_id = c.run_id AND e.chunk_id = c.chunk_id
                    AND e.embedding_model = p.embedding_model
                   WHERE p.run_id = %s AND p.embedding_model = %s
                     AND (p.category_scope = %s OR p.category_scope = '*')
                   GROUP BY p.chunk_count""",
                (category, category, category, run_id, embedding_model, category),
            ).fetchone()
        if row is None:
            raise ValueError("embedding_profile_not_found")
        return int(row["expected_chunk_count"]), int(row["stored_vector_count"])

    def mark_embedding_profile_ready(
        self, run_id: str, embedding_model: str, category: str
    ) -> None:
        expected_count, stored_count = self.embedding_profile_counts(
            run_id, embedding_model, category
        )
        if expected_count != stored_count:
            raise ValueError("embedding_profile_incomplete")
        with self.pool.connection() as connection:
            connection.execute(
                """UPDATE rag.index_run_embedding_profiles
                   SET status = 'ready', updated_at = now()
                   WHERE run_id = %s AND embedding_model = %s
                     AND category_scope = %s AND status IN ('building', 'ready')""",
                (run_id, embedding_model, category),
            )

    def mark_embedding_profile_failed(self, run_id: str, embedding_model: str) -> None:
        with self.pool.connection() as connection:
            connection.execute(
                """UPDATE rag.index_run_embedding_profiles
                   SET status = 'failed', updated_at = now()
                   WHERE run_id = %s AND embedding_model = %s
                     AND status <> 'ready'""",
                (run_id, embedding_model),
            )

    def embedding_target_category_counts(
        self, run_id: str, dataset_version: str
    ) -> dict[str, int]:
        with self.pool.connection() as connection:
            rows = connection.execute(
                """SELECT r.dataset_version, c.category,
                          COUNT(c.chunk_id)::bigint AS target_chunk_count
                   FROM rag.index_runs AS r
                   JOIN rag.evidence_chunks AS c ON c.run_id = r.run_id
                   WHERE r.run_id = %s
                   GROUP BY r.dataset_version, c.category
                   ORDER BY c.category""",
                (run_id,),
            ).fetchall()
        if not rows or any(row["dataset_version"] != dataset_version for row in rows):
            raise ValueError("embedding_target_mismatch")
        return {
            row["category"]: int(row["target_chunk_count"])
            for row in rows
        }

    def embedding_target_chunk_count(
        self, run_id: str, dataset_version: str, category: str
    ) -> int:
        with self.pool.connection() as connection:
            row = connection.execute(
                """SELECT r.dataset_version,
                          COUNT(c.chunk_id) FILTER (
                              WHERE %s::text = '*' OR c.category = %s
                          ) AS target_chunk_count
                   FROM rag.index_runs AS r
                   LEFT JOIN rag.evidence_chunks AS c ON c.run_id = r.run_id
                   WHERE r.run_id = %s
                   GROUP BY r.dataset_version""",
                (category, category, run_id),
            ).fetchone()
        if (
            row is None
            or row["dataset_version"] != dataset_version
            or int(row["target_chunk_count"]) <= 0
        ):
            raise ValueError("embedding_target_mismatch")
        return int(row["target_chunk_count"])

    def search_embedding_vector(
        self,
        run_id: str,
        embedding_model: str,
        vector: Sequence[float],
        limit: int,
        category: str | None = None,
        source_type: str | None = None,
    ) -> list[dict[str, Any]]:
        if len(vector) != 1024:
            raise ValueError("embedding_dimension_mismatch")
        if limit <= 0:
            raise ValueError("invalid_search_limit")
        vector_json = json.dumps([float(value) for value in vector], separators=(",", ":"))
        with self.pool.connection() as connection:
            profile = connection.execute(
                """SELECT dimension, status, category_scope
                   FROM rag.index_run_embedding_profiles
                   WHERE run_id = %s AND embedding_model = %s""",
                (run_id, embedding_model),
            ).fetchone()
            if profile is None or profile["status"] != "ready":
                raise ValueError("embedding_profile_not_ready")
            if profile["dimension"] != 1024:
                raise ValueError("embedding_dimension_mismatch")
            if (
                category is not None
                and profile["category_scope"] != "*"
                and category != profile["category_scope"]
            ):
                raise ValueError("embedding_profile_scope_mismatch")
            rows = connection.execute(
                """WITH query_vector AS (SELECT %s::vector AS embedding)
                   SELECT c.chunk_id, c.category, c.product_id, c.source_type,
                          c.source_id, c.source_field, c.start_offset, c.end_offset,
                          c.evidence_text, c.source_metadata, p.product_payload,
                          e.embedding <=> query_vector.embedding AS distance
                   FROM rag.evidence_chunk_embeddings AS e
                   JOIN rag.index_run_embedding_profiles AS ep
                     ON ep.run_id = e.run_id AND ep.embedding_model = e.embedding_model
                   JOIN rag.evidence_chunks AS c
                     ON c.run_id = e.run_id AND c.chunk_id = e.chunk_id
                   JOIN rag.indexed_products AS p
                     ON p.run_id = c.run_id AND p.category = c.category
                    AND p.product_id = c.product_id
                   CROSS JOIN query_vector
                   WHERE e.run_id = %s AND e.embedding_model = %s
                     AND ep.status = 'ready'
                     AND (ep.category_scope = '*' OR c.category = ep.category_scope)
                     AND (%s::text IS NULL OR c.category = %s)
                     AND (%s::text IS NULL OR c.source_type = %s)
                   ORDER BY e.embedding <=> query_vector.embedding, c.chunk_id ASC
                   LIMIT %s""",
                (
                    vector_json,
                    run_id,
                    embedding_model,
                    category,
                    category,
                    source_type,
                    source_type,
                    limit,
                ),
            ).fetchall()
        return list(rows)

    def search_vector(
        self,
        run_id: str,
        vector: Sequence[float],
        limit: int,
        category: str | None = None,
        source_type: str | None = None,
    ) -> list[dict[str, Any]]:
        if len(vector) != 384:
            raise ValueError("embedding_dimension_mismatch")
        encoded = json.dumps([float(value) for value in vector], separators=(",", ":"))
        with self.pool.connection() as connection:
            rows = connection.execute(
                """SELECT c.chunk_id, c.category, c.product_id, c.source_type,
                          c.source_id, c.source_field, c.start_offset, c.end_offset,
                          c.evidence_text, c.source_metadata, p.product_payload,
                          c.embedding <=> %s::vector AS distance
                   FROM rag.evidence_chunks AS c
                   JOIN rag.indexed_products AS p
                     ON p.run_id = c.run_id AND p.category = c.category
                    AND p.product_id = c.product_id
                   WHERE c.run_id = %s
                     AND (%s::text IS NULL OR c.category = %s)
                     AND (%s::text IS NULL OR c.source_type = %s)
                   ORDER BY distance ASC, c.chunk_id ASC
                   LIMIT %s""",
                (encoded, run_id, category, category, source_type, source_type, limit),
            ).fetchall()
        return list(rows)
