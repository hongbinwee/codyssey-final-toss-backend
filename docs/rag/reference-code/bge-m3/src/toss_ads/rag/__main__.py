"""CLI for indexing the complete source snapshot or serving RAG requests."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from time import perf_counter

from .config import Settings, resolve_bge_m3_cache_path
from .bge_m3 import BGE_M3_MODEL, BGE_M3_MODEL_REVISION
from .embedding_indexer import (
    comparison_database_target,
    index_existing_chunks,
    validate_full_dataset_target,
)
from .indexer import IndexingError, index_dataset
from .source import ProductReviewsClient
from .store import RagStore


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m toss_ads.rag")
    commands = parser.add_subparsers(dest="command", required=True)
    index = commands.add_parser("index", help="build and activate a source snapshot or selected categories")
    index.add_argument(
        "--category",
        dest="categories",
        action="append",
        help="index only this source category; repeat to select multiple categories (default: all)",
    )
    index.add_argument(
        "--resume-run-id",
        help="resume a matching interrupted building run without re-embedding saved chunks",
    )
    serve = commands.add_parser("serve", help="serve POST /v1/rag/search")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8001)
    embed_model = commands.add_parser(
        "embed-model", help="add BGE-M3 vectors to an existing run for comparison"
    )
    embed_model.add_argument("--run-id", required=True)
    embed_model.add_argument("--dataset-version", required=True)
    embedding_scope = embed_model.add_mutually_exclusive_group(required=True)
    embedding_scope.add_argument("--category")
    embedding_scope.add_argument(
        "--all-categories",
        action="store_true",
        help="embed the approved complete test_items2 run across all categories",
    )
    embed_model.add_argument("--batch-size", type=int, default=16)
    embed_model.add_argument("--summary-output", required=True)
    args = parser.parse_args()

    if args.command == "serve":
        import uvicorn

        uvicorn.run("toss_ads.rag.api:app", host=args.host, port=args.port)
        return 0

    if args.command == "embed-model":
        return _embed_existing_model(args)

    try:
        settings = Settings.from_env()
        if settings.embedding_model == BGE_M3_MODEL:
            raise IndexingError("bge_m3_source_indexing_unsupported")
        from .embeddings import create_embedder

        embedder = create_embedder(settings)
        store = RagStore(settings.rag_database_url)
        try:
            with ProductReviewsClient(
                settings.product_source_api_base_url,
                timeout=settings.http_timeout_seconds,
                retries=settings.http_retries,
                max_response_bytes=settings.max_response_bytes,
            ) as client:
                summary = index_dataset(
                    client,
                    store,
                    embedder,
                    settings,
                    resume_run_id=args.resume_run_id,
                    categories=tuple(args.categories) if args.categories else None,
                )
                privacy_counts = dict(client.privacy_redaction_counts)
        finally:
            store.close()
    except IndexingError as error:
        print(f"status=error code={error.code}", file=sys.stderr)
        return 1
    except Exception:
        print("status=error code=configuration_or_startup_failed", file=sys.stderr)
        return 1
    print(
        f"status={summary.status} run_id={summary.run_id} "
        f"dataset_version={summary.dataset_version} "
        f"categories={','.join(sorted(summary.counts.category_counts))} "
        f"products={summary.counts.product_count} "
        f"reviews={summary.counts.review_count} chunks={summary.counts.chunk_count} "
        f"privacy_email_redactions={privacy_counts.get('email', 0)} "
        f"privacy_phone_redactions={privacy_counts.get('phone', 0)} "
        f"privacy_ssn_redactions={privacy_counts.get('ssn', 0)} "
        f"privacy_private_fields_removed={privacy_counts.get('private_fields_removed', 0)}"
    )
    return 0


def _embed_existing_model(args: argparse.Namespace) -> int:
    if args.batch_size < 1 or args.batch_size > 16:
        print("status=error code=invalid_embedding_batch_size", file=sys.stderr)
        return 1
    store = None
    try:
        database_url = os.getenv("RAG_DATABASE_URL", "").strip()
        if not database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("invalid_configuration:RAG_DATABASE_URL")
        comparison_database_target(database_url)
        store = RagStore(database_url)
        # Validate the target before the multi-gigabyte model is loaded.
        category = "*" if getattr(args, "all_categories", False) else args.category
        if category == "*":
            validate_full_dataset_target(
                store, run_id=args.run_id, dataset_version=args.dataset_version
            )
        else:
            store.embedding_target_chunk_count(
                args.run_id, args.dataset_version, category
            )
        from .bge_m3 import BgeM3Embedder

        model_started = perf_counter()
        embedder = BgeM3Embedder(
            max_length=128,
            batch_size=args.batch_size,
            revision=BGE_M3_MODEL_REVISION,
            cache_dir=resolve_bge_m3_cache_path(),
        )
        model_load_seconds = perf_counter() - model_started
        summary = index_existing_chunks(
            store,
            embedder,
            run_id=args.run_id,
            dataset_version=args.dataset_version,
            category=category,
            batch_size=args.batch_size,
            model_load_seconds=model_load_seconds,
        )
        output_path = Path(args.summary_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(summary.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(output_path)
    except ValueError as error:
        print(f"status=error code={error}", file=sys.stderr)
        return 1
    except Exception:
        print("status=error code=embedding_index_failed", file=sys.stderr)
        return 1
    finally:
        if store is not None:
            store.close()

    print(
        f"status={summary.status} run_id={summary.run_id} "
        f"dataset_version={summary.dataset_version} category={summary.category} "
        f"embedding_model={summary.embedding_model} model_revision={summary.model_revision} "
        f"total_chunks={summary.total_chunk_count} "
        f"preexisting_vectors={summary.preexisting_vector_count} "
        f"embedded_chunks={summary.embedded_chunk_count} "
        f"document_embedding_seconds={summary.document_embedding_seconds} "
        f"elapsed_seconds={summary.elapsed_seconds} "
        f"chunks_per_second={summary.chunks_per_second} "
        f"cpu_thread_count={summary.cpu_thread_count} "
        f"model_load_seconds={summary.model_load_seconds} max_rss_mb={summary.max_rss_mb}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
