"""CLI for indexing the complete source snapshot or serving RAG requests."""

from __future__ import annotations

import argparse
import sys

from .config import Settings
from .indexer import IndexingError, index_dataset
from .source import AmazonReviewsClient
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
    args = parser.parse_args()

    if args.command == "serve":
        import uvicorn

        uvicorn.run("toss_ads.rag.api:app", host=args.host, port=args.port)
        return 0

    try:
        settings = Settings.from_env()
        from .embeddings import create_embedder

        embedder = create_embedder(settings)
        store = RagStore(settings.rag_database_url)
        try:
            with AmazonReviewsClient(
                settings.amazon_reviews_api_base_url,
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


if __name__ == "__main__":
    raise SystemExit(main())
