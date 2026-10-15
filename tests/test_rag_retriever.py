from __future__ import annotations

import unittest

from toss_ads.rag.config import Settings
from toss_ads.rag.retriever import hybrid_search
from toss_ads.rag.schemas import RagSearchRequest


class StubStore:
    def __init__(self, rows, review_rows=None):
        self.rows = rows
        self.review_rows = rows if review_rows is None else review_rows
        self.source_type_calls = []

    def active_run(self):
        return {
            "run_id": "run-1",
            "dataset_version": "dataset-v1",
            "embedding_model": Settings("http://source", "postgresql://db").embedding_model,
        }

    def search_bm25(self, run_id, query, limit, category=None, source_type=None):
        if source_type is not None:
            self.source_type_calls.append(("bm25", source_type))
            return self.review_rows if source_type == "review" else []
        return self.rows

    def search_vector(self, run_id, vector, limit, category=None, source_type=None):
        if source_type is not None:
            self.source_type_calls.append(("vector", source_type))
            return self.review_rows if source_type == "review" else []
        return self.rows


class StubEmbedder:
    def embed_query(self, query):
        return [0.0] * 384


class HybridSearchEvidenceTests(unittest.TestCase):
    def test_returns_distinct_chunks_from_the_same_source_field(self):
        shared_review = {
            "category": "Books",
            "product_id": "product-1",
            "source_type": "review",
            "source_id": "review-1",
            "source_field": "reviewText",
            "product_payload": {"title": "Example"},
            "source_metadata": {},
        }
        rows = [
            {
                **shared_review,
                "source_type": "product",
                "source_id": "product-1",
                "source_field": "/title",
                "chunk_id": "title-chunk",
                "evidence_text": "Example",
                "start_offset": 0,
                "end_offset": 7,
            },
            {
                **shared_review,
                "chunk_id": "review-opening",
                "evidence_text": "Opening passage",
                "start_offset": 0,
                "end_offset": 16,
            },
            {
                **shared_review,
                "chunk_id": "review-relevant",
                "evidence_text": "Relevant passage later in the same review",
                "start_offset": 17,
                "end_offset": 58,
            },
        ]
        request = RagSearchRequest(original_question="Find the relevant passage", query="relevant passage")
        store = StubStore(rows)

        response = hybrid_search(
            store,
            StubEmbedder(),
            Settings("http://source", "postgresql://db"),
            request,
        )

        self.assertEqual(response["status"], "ok")
        evidence = response["items"][0]["evidence"]
        self.assertEqual(
            [item["chunk_id"] for item in evidence],
            ["title-chunk", "review-opening", "review-relevant"],
        )
        self.assertEqual(store.source_type_calls, [])

    def test_explicit_review_queries_add_review_only_channels_and_return_review_evidence(self):
        product = {
            "category": "Appliances",
            "product_id": "product-1",
            "source_type": "product",
            "source_id": "product-1",
            "source_field": "/title",
            "chunk_id": "product-title",
            "evidence_text": "Example appliance",
            "start_offset": 0,
            "end_offset": 17,
            "product_payload": {"title": "Example appliance"},
            "source_metadata": {},
        }
        review = {
            **product,
            "source_type": "review",
            "source_id": "a" * 64,
            "source_field": "/text",
            "chunk_id": "review-text",
            "evidence_text": "It worked well on Linux.",
            "start_offset": 0,
            "end_offset": 24,
        }
        product_feature_1 = {
            **product,
            "chunk_id": "product-feature-1",
            "source_field": "/features/0",
        }
        product_feature_2 = {
            **product,
            "chunk_id": "product-feature-2",
            "source_field": "/features/1",
        }
        store = StubStore(
            [product, product_feature_1, product_feature_2, review],
            review_rows=[review],
        )
        request = RagSearchRequest(
            original_question="이 제품의 사용 후기를 찾아줘",
            query="이 제품의 사용 후기를 찾아줘",
        )

        response = hybrid_search(
            store,
            StubEmbedder(),
            Settings("http://source", "postgresql://db"),
            request,
        )

        self.assertEqual(store.source_type_calls, [("bm25", "review"), ("vector", "review")])
        evidence_ids = [item["chunk_id"] for item in response["items"][0]["evidence"]]
        self.assertEqual(evidence_ids, ["review-text", "product-title", "product-feature-1"])
        self.assertAlmostEqual(response["items"][0]["rrf_score"], 2 / 61)
        self.assertEqual(store.source_type_calls, [("bm25", "review"), ("vector", "review")])

    def test_review_only_candidates_do_not_create_rank_gaps(self):
        global_product = {
            "category": "Appliances",
            "product_id": "z-global-product",
            "source_type": "product",
            "source_id": "z-global-product",
            "source_field": "/title",
            "chunk_id": "global-product-title",
            "evidence_text": "Example appliance",
            "start_offset": 0,
            "end_offset": 17,
            "product_payload": {"title": "Example appliance"},
            "source_metadata": {},
        }
        review_only_product = {
            **global_product,
            "product_id": "a-review-only-product",
            "source_id": "b" * 64,
            "source_type": "review",
            "source_field": "/text",
            "chunk_id": "review-only-chunk",
        }
        store = StubStore([global_product], review_rows=[review_only_product])
        request = RagSearchRequest(
            original_question="Find reviews",
            query="Find reviews",
        )

        response = hybrid_search(
            store,
            StubEmbedder(),
            Settings("http://source", "postgresql://db"),
            request,
        )

        self.assertEqual([item["product_id"] for item in response["items"]], ["z-global-product"])
        self.assertEqual(response["items"][0]["evidence"][0]["rrf_rank"], 1)


if __name__ == "__main__":
    unittest.main()
