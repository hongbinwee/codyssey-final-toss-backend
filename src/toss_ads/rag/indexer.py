"""Build a complete, isolated RAG run from the read-only source API."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

import psycopg
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

from .chunker import CHUNKER_VERSION, build_product_chunks, build_review_chunks
from .classification import CATEGORY_POLICY_VERSION, classify_product
from .config import Settings
from .embeddings import count_tokens
from .source import AmazonReviewsClient, SourceError
from .store import RagStore
from .types import (
    EvidenceChunk,
    IndexCounts,
    IndexSummary,
    IndexedProduct,
    QuarantinedProduct,
)


class IndexingError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _price_fields(product: dict[str, Any]) -> tuple[Decimal | None, str | None]:
    amount: Decimal | None = None
    raw_amount = product.get("price")
    if isinstance(raw_amount, (int, float, Decimal)) and not isinstance(raw_amount, bool):
        try:
            parsed = Decimal(str(raw_amount))
            if parsed.is_finite() and parsed >= 0:
                amount = parsed
        except InvalidOperation:
            pass
    currency = product.get("price_currency")
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha():
        currency = None
    else:
        currency = currency.upper()
    return amount, currency


def _counts_payload(counts: IndexCounts) -> dict[str, Any]:
    return {
        "product_count": counts.product_count,
        "review_count": counts.review_count,
        "chunk_count": counts.chunk_count,
        "category_counts": counts.category_counts,
    }


def index_dataset(
    client: AmazonReviewsClient,
    store: RagStore,
    embedder: FastEmbedEmbeddings,
    settings: Settings,
    *,
    resume_run_id: str | None = None,
    categories: tuple[str, ...] | None = None,
) -> IndexSummary:
    try:
        snapshot = client.list_categories()
    except SourceError as error:
        code = "source_version_changed" if error.code == "source_version_changed" else "source_failed"
        raise IndexingError(code) from None
    snapshot_categories = {
        item["category"]: {
            "products": item["product_count"],
            "reviews": item["review_count"],
        }
        for item in snapshot.categories
    }
    if categories is None:
        selected_categories = tuple(sorted(snapshot_categories))
    else:
        selected_categories = tuple(categories)
        if (
            not selected_categories
            or any(not isinstance(name, str) or not name.strip() for name in selected_categories)
            or len(set(selected_categories)) != len(selected_categories)
            or not set(selected_categories).issubset(snapshot_categories)
        ):
            raise IndexingError("invalid_category_scope")
    expected = {name: snapshot_categories[name] for name in selected_categories}
    remaining = {key: dict(value) for key, value in expected.items()}
    category_actual = {
        key: {
            "products": 0,
            "reviews": 0,
            "chunks": 0,
            "source_products": 0,
            "source_reviews": 0,
            "quarantined_products": 0,
            "quarantined_reviews": 0,
        }
        for key in expected
    }
    product_count = review_count = chunk_count = 0
    run_id: str | None = None
    titles: dict[tuple[str, str], str] = {}
    product_batch: list[IndexedProduct] = []
    quarantine_batch: list[QuarantinedProduct] = []
    chunk_batch: list[EvidenceChunk] = []
    quarantined_ids = {key: set() for key in expected}

    def current_counts() -> IndexCounts:
        return IndexCounts(
            product_count=product_count,
            review_count=review_count,
            chunk_count=chunk_count,
            category_counts={key: dict(value) for key, value in sorted(category_actual.items())},
        )

    try:
        chunker_version = f"{CHUNKER_VERSION}:max_tokens={settings.chunk_max_tokens}"
        if resume_run_id is None:
            run_id = store.begin_index_run(
                snapshot.dataset_version,
                settings.embedding_model,
                chunker_version,
                CATEGORY_POLICY_VERSION,
            )
        else:
            run_id = store.resume_index_run(
                resume_run_id,
                snapshot.dataset_version,
                settings.embedding_model,
                chunker_version,
                CATEGORY_POLICY_VERSION,
            )

        def flush_products() -> None:
            if product_batch:
                store.upsert_products(run_id, tuple(product_batch))
                product_batch.clear()

        def flush_quarantined() -> None:
            if quarantine_batch:
                store.record_quarantined_products(run_id, tuple(quarantine_batch))
                quarantine_batch.clear()

        def flush_chunks() -> None:
            if not chunk_batch:
                return
            missing = store.missing_chunks(run_id, tuple(chunk_batch))
            if missing:
                try:
                    vectors = embedder.embed_documents(
                        [chunk.embedding_text for chunk in missing]
                    )
                except Exception:
                    raise IndexingError("embedding_failed") from None
                if len(vectors) != len(missing) or any(
                    len(vector) != 384 for vector in vectors
                ):
                    raise IndexingError("embedding_failed")
                store.upsert_chunks(
                    run_id, tuple(zip(missing, vectors, strict=True))
                )
            chunk_batch.clear()

        for category in sorted(expected):
            for product in client.iter_products(category, snapshot.dataset_version):
                product_id = product.get("parent_asin")
                if not isinstance(product_id, str) or not product_id.strip():
                    raise IndexingError("invalid_source_linkage")
                remaining[category]["products"] -= 1
                category_actual[category]["source_products"] += 1
                quarantine = classify_product(category, snapshot.dataset_version, product)
                if quarantine is not None:
                    quarantine_batch.append(quarantine)
                    quarantined_ids[category].add(product_id)
                    category_actual[category]["quarantined_products"] += 1
                    if len(quarantine_batch) >= 100:
                        flush_quarantined()
                    continue
                amount, currency = _price_fields(product)
                product_batch.append(
                    IndexedProduct(
                        dataset_version=snapshot.dataset_version,
                        category=category,
                        product_id=product_id,
                        product_payload=product,
                        price_amount=amount,
                        price_currency=currency,
                    )
                )
                title = product.get("title")
                titles[(category, product_id)] = title if isinstance(title, str) else ""
                product_chunks = build_product_chunks(
                    product,
                    category,
                    snapshot.dataset_version,
                    max_tokens=settings.chunk_max_tokens,
                    count_tokens=lambda text: count_tokens(embedder, text),
                )
                chunk_batch.extend(product_chunks)
                category_actual[category]["products"] += 1
                category_actual[category]["chunks"] += len(product_chunks)
                product_count += 1
                chunk_count += len(product_chunks)
                if len(product_batch) >= 100 or len(chunk_batch) >= settings.embedding_batch_size:
                    flush_products()
                    flush_quarantined()
                    flush_chunks()
            flush_products()
            flush_quarantined()
            flush_chunks()

            for review in client.iter_reviews(category, snapshot.dataset_version):
                product_id = review.get("parent_asin")
                if not isinstance(product_id, str) or not product_id.strip():
                    raise IndexingError("invalid_source_linkage")
                remaining[category]["reviews"] -= 1
                category_actual[category]["source_reviews"] += 1
                if product_id in quarantined_ids[category]:
                    category_actual[category]["quarantined_reviews"] += 1
                    continue
                title_key = (category, product_id) if isinstance(product_id, str) else None
                if title_key is None or title_key not in titles:
                    raise IndexingError("invalid_source_linkage")
                review_chunks = build_review_chunks(
                    review,
                    titles[title_key],
                    category,
                    snapshot.dataset_version,
                    max_tokens=settings.chunk_max_tokens,
                    count_tokens=lambda text: count_tokens(embedder, text),
                )
                chunk_batch.extend(review_chunks)
                category_actual[category]["reviews"] += 1
                category_actual[category]["chunks"] += len(review_chunks)
                review_count += 1
                chunk_count += len(review_chunks)
                if len(chunk_batch) >= settings.embedding_batch_size:
                    flush_chunks()
            flush_chunks()

        if any(
            values["products"] != 0 or values["reviews"] != 0
            for values in remaining.values()
        ):
            raise IndexingError("source_count_mismatch")
        final_snapshot = client.list_categories()
        if final_snapshot.dataset_version != snapshot.dataset_version:
            raise IndexingError("source_version_changed")
        final_counts = {
            item["category"]: (item["product_count"], item["review_count"])
            for item in final_snapshot.categories
        }
        original_counts = {
            item["category"]: (item["product_count"], item["review_count"])
            for item in snapshot.categories
        }
        if final_counts != original_counts:
            raise IndexingError("source_count_mismatch")

        counts = current_counts()
        store.activate_dataset(run_id, _counts_payload(counts))
        return IndexSummary(run_id, snapshot.dataset_version, "active", counts)
    except SourceError as error:
        code = "source_version_changed" if error.code == "source_version_changed" else "source_failed"
        if run_id is not None:
            try:
                store.fail_index_run(run_id, code, _counts_payload(current_counts()))
            except Exception:
                pass
        raise IndexingError(code) from None
    except IndexingError as error:
        if run_id is not None:
            try:
                store.fail_index_run(run_id, error.code, _counts_payload(current_counts()))
            except Exception:
                pass
        raise
    except psycopg.Error:
        if run_id is not None:
            try:
                store.fail_index_run(run_id, "database_failed", _counts_payload(current_counts()))
            except Exception:
                pass
        raise IndexingError("database_failed") from None
    except Exception:
        if run_id is not None:
            try:
                store.fail_index_run(run_id, "index_failed", _counts_payload(current_counts()))
            except Exception:
                pass
        raise IndexingError("index_failed") from None
