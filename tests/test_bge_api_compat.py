from __future__ import annotations

from contextlib import nullcontext
from dataclasses import replace
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from toss_ads.rag.api import create_app, TEST_ITEMS_DATASET_VERSION
from toss_ads.rag.config import Settings
from toss_ads.rag.embeddings import create_embedder
from toss_ads.rag.bge_m3 import BgeM3Embedder
from toss_ads.rag.retriever import HybridRagRetriever
from toss_ads.rag.store import RagStore

MODEL = "BAAI/bge-m3"
REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
COUNT = 114106
MINILM = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def settings(model=MODEL):
    return Settings(
        rag_database_url="postgresql://reader@127.0.0.1:5432/toss_rag",
        embedding_model=model, default_profile="test_items2",
    )


class Embedder:
    def __init__(self, dimension=1024):
        self.dimension = dimension
        self.queries = []

    def embed_query(self, query):
        self.queries.append(query)
        return [0.01] * self.dimension


class Store:
    def __init__(self):
        self.profile = {"status": "ready", "category_scope": "*", "dimension": 1024,
                        "model_revision": REVISION, "max_input_tokens": 128, "chunk_count": COUNT}
        self.stored_count = COUNT
        self.calls = []
        self.active_profiles = []
        self.payload = {"title": "통학용 백팩", "brand": "test", "category": "fashion",
                        "source_dataset": "test_items2", "features": {"canonical_product_type": "backpack"}}

    def active_run(self, profile="all_products"):
        self.active_profiles.append(profile)
        return {"run_id": "run-new" if profile == "test_items2" else "run-old",
                "dataset_version": "test_items2:v6.1-review-refined" if profile == "test_items2" else TEST_ITEMS_DATASET_VERSION,
                "embedding_model": MINILM}

    def supported_categories(self, run_id):
        return ["beauty", "fashion", "food", "living"] if run_id == "run-new" else ["beauty"]

    def embedding_profile_info(self, *args):
        return self.profile

    def embedding_target_chunk_count(self, *args):
        return COUNT

    def embedding_profile_counts(self, *args):
        return COUNT, self.stored_count

    def product_catalog(self, run_id, category):
        return [{"product_id": p, "category": "fashion", "product_payload": self.payload} for p in ["p1", "p2"]]

    def _rows(self):
        text = "통학할 때 매일 사용한 백팩으로 수납하기 편했어요."
        return [{"chunk_id": "c" * 64, "category": "fashion", "product_id": "p1", "source_type": "review",
                 "source_id": "review-1", "source_field": "/text", "start_offset": 0, "end_offset": len(text),
                 "evidence_text": text, "source_metadata": {"source_kind": "REAL"}, "product_payload": self.payload}]

    def search_bm25(self, *args, **kwargs):
        self.calls.append(("bm25", args, kwargs))
        return self._rows()

    def search_embedding_vector(self, *args, **kwargs):
        self.calls.append(("bge", args, kwargs))
        return self._rows()

    def search_vector(self, *args, **kwargs):
        self.calls.append(("minilm", args, kwargs))
        return self._rows()

    def list_test_items(self, *args):
        return [], 0

    def test_item_review_chunks(self, *args):
        return []


class Commerce:
    def __init__(self):
        self.calls = []

    def lookup(self, products, filters, require_stock):
        self.calls.append((products, filters, require_stock))
        # This double supplies an already verified eligibility decision;
        # the test checks that retrieval honors it, not Commerce SQL correctness.
        return {("fashion", "p1"): {"variant_id": "v1", "unit_price_won": 49000, "stock_qty": 3,
                    "is_simulated": False, "source_price_evidence_status": "CANDIDATE"}}


class BgeApiCompatibilityTests(unittest.TestCase):
    def test_langchain_retriever_accepts_bge_embedder(self):
        embedder = BgeM3Embedder(model=object(), model_revision=REVISION)
        store = RagStore.__new__(RagStore)
        try:
            retriever = HybridRagRetriever(store=store, embedder=embedder, settings=settings())
        except Exception as exc:
            self.fail(f"BGE retriever construction failed: {type(exc).__name__}: {exc}")
        self.assertIs(retriever.embedder, embedder)

    def request(self):
        return {"request_id": "compat-001", "original_question": "통학용 백팩을 5만원 이하로 찾아줘. 후기도 궁금해",
                "query": "백팩 후기", "category": "fashion", "profile": "test_items2", "product_type": "backpack",
                "filters": {"price_max": 50000, "currency": "KRW", "in_stock": True}, "top_k": 3}

    def test_ready_bge_health_preserves_profile_and_commerce_metadata(self):
        app = create_app(settings(), store=Store(), embedder=Embedder(), commerce=Commerce())
        with TestClient(app) as client:
            response = client.get("/healthz")
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["profile_name"], "test_items2")
        self.assertTrue(response.json()["commerce_configured"])

    def test_extended_03_request_executes_bge_after_commerce_eligibility(self):
        store, embedder, commerce = Store(), Embedder(), Commerce()
        app = create_app(settings(), store=store, embedder=embedder, commerce=commerce)
        with TestClient(app) as client:
            response = client.post("/v1/rag/search", json=self.request())
        self.assertEqual(response.status_code, 200, response.json())
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["profile_name"], "test_items2")
        self.assertEqual(body["items"][0]["commerce"]["variant_id"], "v1")
        self.assertEqual(body["items"][0]["product_metadata"]["price"]["amount_won"], 49000)
        self.assertEqual(body["applied_filters"]["price_max"], 50000)
        self.assertTrue(body["applied_filters"]["in_stock"])
        self.assertEqual(commerce.calls[0][1].price_max, 50000)
        self.assertTrue(commerce.calls[0][2])
        self.assertEqual({p["product_id"] for p in commerce.calls[0][0]}, {"p1", "p2"})
        bge = [call for call in store.calls if call[0] == "bge"]
        self.assertTrue(bge)
        self.assertTrue(all(call[2]["product_ids"] == ["p1"] for call in bge))
        self.assertTrue(all(len(call[1][2]) == 1024 for call in bge))
        self.assertFalse(any(call[0] == "minilm" for call in store.calls))
        self.assertEqual(store.active_profiles, ["test_items2"])

    def test_partial_or_wrong_revision_profile_is_rejected_before_encoding(self):
        for change in ({"status": "building"}, {"model_revision": "wrong"}, {"category_scope": "beauty"}):
            with self.subTest(change=change):
                store, embedder = Store(), Embedder()
                store.profile.update(change)
                app = create_app(settings(), store=store, embedder=embedder, commerce=Commerce())
                with TestClient(app) as client:
                    response = client.post("/v1/rag/search", json=self.request())
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()["error_code"], "index_not_ready")
                self.assertEqual(embedder.queries, [])
                self.assertEqual(store.calls, [])

    def test_missing_vectors_make_bge_not_ready(self):
        store = Store()
        store.stored_count -= 1
        app = create_app(settings(), store=store, embedder=Embedder(), commerce=Commerce())
        with TestClient(app) as client:
            response = client.get("/healthz")
        self.assertEqual(response.json()["status"], "not_ready")
        self.assertEqual(response.json()["error_code"], "index_not_ready")

    def test_minilm_configuration_still_uses_original_vector_path(self):
        store = Store()
        app = create_app(settings(MINILM), store=store, embedder=Embedder(384), commerce=Commerce())
        with TestClient(app) as client:
            response = client.post("/v1/rag/search", json=self.request())
        self.assertEqual(response.status_code, 200, response.json())
        self.assertTrue(any(call[0] == "minilm" for call in store.calls))
        self.assertFalse(any(call[0] == "bge" for call in store.calls))

    def test_legacy_catalog_paths_are_present_and_stay_pinned(self):
        store = Store()
        app = create_app(settings(), store=store, embedder=Embedder(), commerce=Commerce())
        with TestClient(app) as client:
            catalog = client.get("/v1/catalog/test-items?limit=1")
            reviews = client.get("/v1/catalog/test-items/old-product/reviews")
        self.assertEqual(catalog.status_code, 200)
        self.assertEqual(catalog.json()["dataset_version"], TEST_ITEMS_DATASET_VERSION)
        self.assertEqual(reviews.status_code, 200)
        self.assertEqual(store.active_profiles, ["all_products", "all_products"])

    def test_factory_selects_bge_instead_of_fastembed(self):
        fast = Mock()
        fast.model.embedding_size = 384
        marker = object()
        with patch("toss_ads.rag.embeddings.FastEmbedEmbeddings", return_value=fast), patch(
            "toss_ads.rag.embeddings.BgeM3Embedder", create=True, return_value=marker
        ) as bge:
            self.assertIs(create_embedder(settings()), marker)
        self.assertEqual(bge.call_args.kwargs["revision"], REVISION)


class BgeSqlEligibilityTests(unittest.TestCase):
    def test_bge_sql_limits_candidates_to_verified_product_ids(self):
        self.assertTrue(hasattr(RagStore, "search_embedding_vector"), "BGE serving lookup is missing")
        calls = []
        class Cursor:
            def fetchone(self):
                return {"status": "ready", "dimension": 1024, "category_scope": "*"}
            def fetchall(self):
                return []
        class Connection:
            def execute(self, sql, parameters):
                calls.append((sql, parameters))
                return Cursor()
        store = RagStore.__new__(RagStore)
        store.pool = Mock()
        store.pool.connection.return_value = nullcontext(Connection())
        store.search_embedding_vector("run", MODEL, [0.0] * 1024, 20, "fashion", product_ids=["p1"])
        self.assertIn("c.product_id = ANY", calls[-1][0])
        self.assertIn(["p1"], calls[-1][1])


if __name__ == "__main__":
    unittest.main()
