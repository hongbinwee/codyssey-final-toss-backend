from __future__ import annotations

from contextlib import contextmanager
import unittest

from fastapi.testclient import TestClient

from toss_ads.rag.api import create_app
from toss_ads.rag.config import DEFAULT_MODEL, Settings
from toss_ads.rag.schemas import RagSearchRequest
from toss_ads.rag.store import RagStore


PRODUCT_IDS = ["p-v4-o-0035", "p-v4-o-0043", "p-v4-o-0051"]
DATASET_VERSION = "test_items2:v6.1-review-refined"


def test_settings() -> Settings:
    return Settings(
        rag_database_url="postgresql://reader@127.0.0.1:5432/toss_rag",
        embedding_model=DEFAULT_MODEL,
        default_profile="test_items2",
    )


class Embedder:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def embed_query(self, query: str) -> list[float]:
        self.queries.append(query)
        return [0.01] * 384


class ScopedSearchStore:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.ignore_filters = False
        self.products = [
            {
                "product_id": product_id,
                "category": "beauty",
                "product_payload": {
                    "title": f"보습 크림 {index}",
                    "brand": "QA13-B",
                    "source_dataset": "test_items2",
                    "features": {"canonical_product_type": "moisturizer"},
                },
            }
            for index, product_id in enumerate(PRODUCT_IDS, 1)
        ]
        self.rows = [
            self._row(
                PRODUCT_IDS[0],
                "review-0035-01",
                "처음 바를 때는 촉촉했지만, 몇 시간 지나자 피부가 다시 당기고 건조해졌어요.",
                "option-0035",
            ),
            self._row(
                PRODUCT_IDS[1],
                "review-0043-02",
                "처음에는 촉촉했는데 저녁이 되니 피부가 건조하고 당겼습니다.",
                "option-0043",
            ),
            self._row(
                PRODUCT_IDS[2],
                "review-0051-03",
                "향은 두 시간쯤 지나면 거의 사라져요.",
                "option-0051",
            ),
            self._row(
                "outside-product",
                "outside-review",
                "처음엔 촉촉했지만 몇 시간 뒤 건조해졌어요.",
                "outside-option",
            ),
            self._row(
                PRODUCT_IDS[0],
                "product-description",
                "하루 종일 촉촉한 보습감을 제공하는 크림입니다.",
                "option-0035",
                source_type="product",
            ),
        ]

    @staticmethod
    def _row(
        product_id: str,
        source_id: str,
        text: str,
        variant_id: str,
        *,
        source_type: str = "review",
    ) -> dict[str, object]:
        return {
            "chunk_id": f"chunk-{source_id}",
            "category": "beauty",
            "product_id": product_id,
            "source_type": source_type,
            "source_id": source_id,
            "source_field": "/text",
            "start_offset": 0,
            "end_offset": len(text),
            "evidence_text": text,
            "source_metadata": {"variant_id": variant_id, "source_kind": "REAL"},
            "product_payload": {
                "title": f"보습 크림 {product_id}",
                "source_dataset": "test_items2",
                "features": {"canonical_product_type": "moisturizer"},
            },
        }

    def active_run(self, profile: str) -> dict[str, str]:
        return {
            "run_id": "run-test-items2",
            "dataset_version": DATASET_VERSION,
            "embedding_model": DEFAULT_MODEL,
        }

    def supported_categories(self, run_id: str) -> list[str]:
        return ["beauty"]

    def product_catalog(self, run_id: str, category: str | None) -> list[dict[str, object]]:
        return [row for row in self.products if category is None or row["category"] == category]

    def _search(
        self,
        method: str,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> list[dict[str, object]]:
        self.calls.append({"method": method, "args": args, **kwargs})
        source_type = kwargs.get("source_type")
        product_ids = kwargs.get("product_ids")
        rows = self.rows
        if self.ignore_filters:
            return rows
        if source_type is not None:
            rows = [row for row in rows if row["source_type"] == source_type]
        if product_ids is not None:
            rows = [row for row in rows if row["product_id"] in product_ids]
        return rows

    def search_bm25(self, *args: object, **kwargs: object) -> list[dict[str, object]]:
        return self._search("bm25", args, kwargs)

    def search_vector(self, *args: object, **kwargs: object) -> list[dict[str, object]]:
        return self._search("vector", args, kwargs)


class MustNotCallCommerce:
    def lookup(self, *_args: object, **_kwargs: object) -> dict[tuple[str, str], object]:
        raise AssertionError("review-only search must not be filtered by current stock")


def scoped_payload(product_ids: list[str] | None = None) -> dict[str, object]:
    return {
        "request_id": "qa13b-review-search-001",
        "original_question": "이 중에 처음 촉촉하지만 몇 시간 지나면 건조해진다는 리뷰가 있는 제품 찾아줘",
        "query": "처음에는 촉촉하지만 몇 시간 뒤 피부가 건조하고 당기는 사용 경험",
        "category": "beauty",
        "filters": {},
        "product_ids": product_ids if product_ids is not None else PRODUCT_IDS,
        "source_type": "review",
        "top_k": 5,
    }


class ScopedReviewSchemaTests(unittest.TestCase):
    def test_scoped_review_request_accepts_canonical_fields(self) -> None:
        request = RagSearchRequest.model_validate(scoped_payload())
        self.assertEqual(request.product_ids, PRODUCT_IDS)
        self.assertEqual(request.source_type, "review")

    def test_review_only_requires_an_explicit_product_scope(self) -> None:
        payload = scoped_payload()
        payload.pop("product_ids")
        with self.assertRaises(ValueError):
            RagSearchRequest.model_validate(payload)

    def test_product_scope_rejects_duplicates_more_than_three_and_non_strings(self) -> None:
        for product_ids in (
            [PRODUCT_IDS[0], PRODUCT_IDS[0]],
            [*PRODUCT_IDS, "p-v4-o-0060"],
            [PRODUCT_IDS[0], 43],
            ["   "],
        ):
            with self.subTest(product_ids=product_ids), self.assertRaises(ValueError):
                RagSearchRequest.model_validate(scoped_payload(product_ids))

    def test_review_scope_keeps_existing_commerce_filters_in_the_contract(self) -> None:
        payload = scoped_payload()
        payload["filters"] = {"in_stock": True}
        request = RagSearchRequest.model_validate(payload)
        self.assertTrue(request.filters.in_stock)


class ScopedReviewSearchTests(unittest.TestCase):
    def test_semantic_review_search_stays_inside_requested_ids_and_preserves_evidence(self) -> None:
        store = ScopedSearchStore()
        embedder = Embedder()
        app = create_app(test_settings(), store=store, embedder=embedder, commerce=MustNotCallCommerce())
        with TestClient(app) as client:
            response = client.post("/v1/rag/search", json=scoped_payload())

        self.assertEqual(response.status_code, 200, response.json())
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["dataset_version"], DATASET_VERSION)
        self.assertEqual(body["applied_filters"]["product_ids"], PRODUCT_IDS)
        self.assertEqual(body["applied_filters"]["source_type"], "review")
        self.assertEqual({item["product_id"] for item in body["items"]}, set(PRODUCT_IDS))
        self.assertTrue(all(item["commerce"]["validation_status"] == "unverified" for item in body["items"]))

        evidence = [e for item in body["items"] for e in item["evidence"]]
        self.assertTrue(evidence)
        self.assertTrue(all(e["source_type"] == "review" for e in evidence))
        self.assertTrue(all(e["product_id"] in PRODUCT_IDS for e in evidence))
        self.assertTrue(all(e["source_id"].startswith("review-") for e in evidence))
        self.assertTrue(all(e["source_version"] == DATASET_VERSION for e in evidence))
        self.assertTrue(all("variant_id" in e["source_metadata"] for e in evidence))
        self.assertTrue(any("몇 시간" in e["evidence_text"] and "건조" in e["evidence_text"] for e in evidence))
        self.assertEqual(len(embedder.queries), 1)
        self.assertEqual(embedder.queries[0], scoped_payload()["query"])

        self.assertEqual({call["method"] for call in store.calls}, {"bm25", "vector"})
        self.assertTrue(all(call["source_type"] == "review" for call in store.calls))
        self.assertTrue(all(call["product_ids"] == PRODUCT_IDS for call in store.calls))
        self.assertEqual(body["search_context"]["result_limit_semantics"], "products")

    def test_unknown_ids_return_no_results_without_searching_other_products(self) -> None:
        store = ScopedSearchStore()
        app = create_app(test_settings(), store=store, embedder=Embedder())
        with TestClient(app) as client:
            response = client.post(
                "/v1/rag/search",
                json=scoped_payload(["unknown-product"]),
            )

        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(response.json()["status"], "no_results")
        self.assertEqual(response.json()["items"], [])
        self.assertEqual(store.calls, [])

    def test_top_k_still_limits_products_not_evidence_chunks(self) -> None:
        store = ScopedSearchStore()
        app = create_app(test_settings(), store=store, embedder=Embedder())
        payload = scoped_payload()
        payload["top_k"] = 1
        with TestClient(app) as client:
            response = client.post("/v1/rag/search", json=payload)

        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(len(response.json()["items"]), 1)
        self.assertEqual(response.json()["search_context"]["result_limit_semantics"], "products")
        self.assertLessEqual(len(response.json()["items"][0]["evidence"]), 3)

    def test_backend_that_ignores_filters_fails_closed_without_leaking_rows(self) -> None:
        store = ScopedSearchStore()
        store.ignore_filters = True
        app = create_app(test_settings(), store=store, embedder=Embedder())
        with TestClient(app) as client:
            response = client.post("/v1/rag/search", json=scoped_payload())

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error_code"], "search_failed")
        self.assertEqual(response.json()["items"], [])

    def test_invalid_scope_is_422_and_does_not_start_search(self) -> None:
        store = ScopedSearchStore()
        app = create_app(test_settings(), store=store, embedder=Embedder())
        with TestClient(app) as client:
            for invalid_ids in (
                [PRODUCT_IDS[0], PRODUCT_IDS[0]],
                [*PRODUCT_IDS, "fourth-product"],
                [PRODUCT_IDS[0], 12],
            ):
                with self.subTest(product_ids=invalid_ids):
                    response = client.post(
                        "/v1/rag/search",
                        json=scoped_payload(invalid_ids),
                    )
                    self.assertEqual(response.status_code, 422, response.json())
        self.assertEqual(store.calls, [])


class _Cursor:
    def fetchone(self) -> dict[str, object]:
        return {"dimension": 1024, "status": "ready", "category_scope": "*"}

    def fetchall(self) -> list[dict[str, object]]:
        return []


class _Connection:
    def __init__(self, calls: list[tuple[str, tuple[object, ...]]]) -> None:
        self.calls = calls

    def execute(self, sql: str, parameters: tuple[object, ...], **_kwargs: object) -> _Cursor:
        self.calls.append((sql, parameters))
        return _Cursor()


class _Pool:
    def __init__(self, calls: list[tuple[str, tuple[object, ...]]]) -> None:
        self.connection_object = _Connection(calls)

    @contextmanager
    def connection(self):
        yield self.connection_object


class ScopedSearchSqlTests(unittest.TestCase):
    def test_bm25_minilm_and_bge_sql_filter_before_limit(self) -> None:
        calls: list[tuple[str, tuple[object, ...]]] = []
        store = RagStore.__new__(RagStore)
        store.pool = _Pool(calls)
        ids = PRODUCT_IDS[:2]

        store.search_bm25("run-1", "촉촉한 뒤 건조", 12, "beauty", "review", ids)
        store.search_vector("run-1", [0.01] * 384, 12, "beauty", "review", ids)
        store.search_embedding_vector("run-1", "BAAI/bge-m3", [0.01] * 1024, 12, "beauty", "review", ids)

        query_calls = [call for call in calls if "LIMIT %s" in call[0]]
        self.assertEqual(len(query_calls), 3)
        for sql, parameters in query_calls:
            normalized_sql = " ".join(sql.split())
            limit_at = normalized_sql.index("LIMIT %s")
            self.assertLess(normalized_sql.index("c.source_type = %s"), limit_at)
            self.assertLess(normalized_sql.index("c.product_id = ANY(%s::text[])") , limit_at)
            self.assertIn("review", parameters)
            self.assertIn(ids, parameters)


if __name__ == "__main__":
    unittest.main()
