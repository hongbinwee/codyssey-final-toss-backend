from __future__ import annotations

import hashlib
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

import psycopg
from fastapi.testclient import TestClient
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_core.callbacks import BaseCallbackHandler

from toss_ads.rag.api import TEST_ITEMS_DATASET_VERSION, create_app
from toss_ads.rag.config import Settings
from toss_ads.rag.retriever import HybridRagRetriever, SearchError
from toss_ads.rag.schemas import RagSearchRequest
from toss_ads.rag.store import RagStore


class MemoryStore(RagStore):
    """Replace only external database I/O; use real retrieval and API code."""

    def __init__(self, *, empty=False, fail_search=False):
        self.empty = empty
        self.fail_search = fail_search
        self.search_calls = []

    def active_run(self, profile_name="all_products"):
        return {
            "run_id": "test-items-run",
            "dataset_version": TEST_ITEMS_DATASET_VERSION,
            "embedding_model": Settings("http://unused", "postgresql://unused").embedding_model,
        }

    def supported_categories(self, run_id):
        return ["beauty"]

    def _rows(self):
        if self.fail_search:
            raise psycopg.OperationalError("private database connection information")
        if self.empty:
            return []
        return [{
            "chunk_id": hashlib.sha256(str(i).encode()).hexdigest(),
            "category": "beauty",
            "product_id": f"product-{i}",
            "source_type": "review",
            "source_id": f"review-{i}",
            "source_field": "/body",
            "start_offset": 0,
            "end_offset": 18,
            "evidence_text": f"Birthday gift review {i}",
            "source_metadata": {"rating": 5, "commerce_review_id": f"review-{i}"},
            "product_payload": {"title": f"Gift {i}", "brand": "Fixture"},
        } for i in range(3)]

    def search_bm25(self, run_id, query, limit, category=None, source_type=None):
        self.search_calls.append(("bm25", query, category, source_type))
        return self._rows()

    def search_vector(self, run_id, vector, limit, category=None, source_type=None):
        self.search_calls.append(("vector", None, category, source_type))
        return self._rows()


class LocalEmbedder(FastEmbedEmbeddings):
    def embed_query(self, text):
        if text == "embedding-error":
            raise RuntimeError("private embedding error")
        return [0.0] * 384


class RecordingCallbacks(BaseCallbackHandler):
    def __init__(self, barrier=None):
        self.events = []
        self.barrier = barrier

    def on_retriever_start(self, serialized, query, **kwargs):
        self.events.append(("start", query))

    def on_retriever_end(self, documents, **kwargs):
        self.events.append(("end", len(documents)))
        if self.barrier:
            self.barrier.wait(timeout=5)

    def on_retriever_error(self, error, **kwargs):
        self.events.append(("error", str(error)))


class LangChainHttpTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings("http://unused", "postgresql://unused")
        # No model download: only the external embedding computation is replaced.
        self.embedder = LocalEmbedder.model_construct()
        self.store = MemoryStore()

    def request(self, **overrides):
        return {
            "request_id": "request-one",
            "original_question": "생일 선물용 리뷰를 찾아줘",
            "query": "birthday gift",
            "category": "beauty",
            "top_k": 1,
            **overrides,
        }

    def retriever(self, **overrides):
        return HybridRagRetriever(
            store=self.store, embedder=self.embedder, settings=self.settings, **overrides,
        )

    def app(self, **overrides):
        return create_app(self.settings, store=overrides.get("store", self.store), embedder=self.embedder)

    def test_http_search_runs_langchain_and_keeps_requested_result_count(self):
        with TestClient(self.app()) as client:
            with self.assertLogs("toss_ads.rag.retriever", level="INFO") as logs:
                response = client.post("/v1/rag/search", json=self.request(top_k=2))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["request_id"], "request-one")
        self.assertEqual(payload["dataset_version"], TEST_ITEMS_DATASET_VERSION)
        self.assertEqual(payload["applied_filters"], {"category": "beauty"})
        self.assertEqual(len(payload["items"]), 2)
        self.assertTrue(any("langchain_retriever" in entry and "request-one" in entry for entry in logs.output))

    def test_structured_search_preserves_original_question_conditions_and_callbacks(self):
        callbacks = RecordingCallbacks()
        request = RagSearchRequest.model_validate(self.request(
            filters={"price_max": 30000, "currency": "KRW"},
            required_conditions=["fragrance free"], preferences=["lightweight"],
        ))
        result = self.retriever().search(request, config={"callbacks": [callbacks]})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(len(result["unverified_conditions"]), 3)
        self.assertIn("확인되지 않은 필수 조건: fragrance free", result["unverified_conditions"])
        self.assertIn("확인되지 않은 선호 조건: lightweight", result["unverified_conditions"])
        self.assertIn(("bm25", "birthday gift", "beauty", "review"), self.store.search_calls)
        self.assertEqual(callbacks.events[0], ("start", "birthday gift"))
        self.assertEqual(callbacks.events[-1][0], "end")

    def test_unsupported_category_remains_an_error_with_metadata(self):
        with TestClient(self.app()) as client:
            response = client.post("/v1/rag/search", json=self.request(category="food"))
        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error_code"], "unsupported_category")
        self.assertEqual(payload["request_id"], "request-one")
        self.assertEqual(payload["dataset_version"], TEST_ITEMS_DATASET_VERSION)
        self.assertEqual(payload["supported_categories"], ["beauty"])
        self.assertEqual(payload["items"], [])

    def test_empty_results_keep_no_results_status(self):
        with TestClient(self.app(store=MemoryStore(empty=True))) as client:
            response = client.post("/v1/rag/search", json=self.request())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "no_results")
        self.assertEqual(response.json()["items"], [])

    def test_low_relevance_keeps_its_status(self):
        settings = Settings("http://unused", "postgresql://unused", min_rrf_score=1.0)
        app = create_app(settings, store=self.store, embedder=self.embedder)
        with TestClient(app) as client:
            response = client.post("/v1/rag/search", json=self.request())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "low_relevance")
        self.assertEqual(response.json()["items"], [])

    def test_database_failure_remains_a_safe_service_error(self):
        with TestClient(self.app(store=MemoryStore(fail_search=True))) as client:
            with self.assertLogs("toss_ads.rag", level="WARNING") as logs:
                response = client.post("/v1/rag/search", json=self.request())
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error_code"], "database_failed")
        self.assertNotIn("private", response.text)
        self.assertNotIn("private", " ".join(logs.output))

    def test_embedding_failure_remains_a_service_error(self):
        with TestClient(self.app()) as client:
            response = client.post("/v1/rag/search", json=self.request(query="embedding-error"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error_code"], "embedding_failed")
        self.assertEqual(response.json()["items"], [])

    def test_invalid_request_is_rejected_before_search(self):
        with TestClient(self.app()) as client:
            response = client.post("/v1/rag/search", json=self.request(top_k=0))
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error_code"], "invalid_request")
        self.assertEqual(self.store.search_calls, [])

    def test_document_interface_preserves_evidence_and_source_metadata(self):
        documents = self.retriever().invoke("birthday gift")
        self.assertEqual(len(documents), 3)
        self.assertEqual(documents[0].page_content, "Birthday gift review 0")
        self.assertEqual(documents[0].metadata["source_id"], "review-0")
        self.assertEqual(documents[0].metadata["source_version"], TEST_ITEMS_DATASET_VERSION)

    def test_document_interface_raises_on_search_error(self):
        request = RagSearchRequest.model_validate(self.request(category="food"))
        with self.assertRaisesRegex(SearchError, "unsupported_category"):
            self.retriever(search_request=request).invoke(request.query)

    def test_parallel_requests_keep_separate_response_artifacts(self):
        # Both invocations finish retrieval before either reads its response.
        callbacks = RecordingCallbacks(threading.Barrier(2))
        retriever = self.retriever()
        first = RagSearchRequest.model_validate(self.request(request_id="first", top_k=1))
        second = RagSearchRequest.model_validate(self.request(request_id="second", top_k=2))
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(
                lambda request: retriever.search(request, config={"callbacks": [callbacks]}),
                [first, second],
            ))
        self.assertEqual([result["request_id"] for result in results], ["first", "second"])
        self.assertEqual([len(result["items"]) for result in results], [1, 2])


if __name__ == "__main__":
    unittest.main()
