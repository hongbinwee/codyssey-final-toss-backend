from __future__ import annotations

import unittest

from toss_ads.rag.config import Settings
from toss_ads.rag.indexer import IndexingError, index_dataset
from toss_ads.rag.types import CategorySnapshot


class FakeSource:
    def __init__(self):
        self.product_categories = []
        self.review_categories = []
        self.snapshot = CategorySnapshot(
            "dataset-v1",
            (
                {"category": "Appliances", "product_count": 1, "review_count": 0},
                {"category": "Clothing_Shoes_and_Jewelry", "product_count": 1, "review_count": 0},
            ),
        )

    def list_categories(self):
        return self.snapshot

    def iter_products(self, category, dataset_version):
        self.product_categories.append(category)
        yield {
            "parent_asin": f"product-{category}",
            "title": f"Sample {category} item",
            "main_category": category,
            "categories": [category],
        }

    def iter_reviews(self, category, dataset_version):
        self.review_categories.append(category)
        return iter(())


class FakeEmbedderModel:
    def token_count(self, text):
        return len(text.split()) + 2


class FakeEmbedder:
    model = FakeEmbedderModel()

    def embed_documents(self, texts):
        return [[0.0] * 384 for _ in texts]


class FakeStore:
    def __init__(self):
        self.products = []
        self.activated_counts = None
        self.begin_calls = 0

    def begin_index_run(self, *args):
        self.begin_calls += 1
        return "run-1"

    def resume_index_run(self, *args):
        return args[0]

    def upsert_products(self, run_id, products):
        self.products.extend(products)

    def record_quarantined_products(self, run_id, products):
        pass

    def missing_chunks(self, run_id, chunks):
        return tuple(chunks)

    def upsert_chunks(self, run_id, chunks_and_vectors):
        pass

    def activate_dataset(self, run_id, counts):
        self.activated_counts = counts

    def fail_index_run(self, *args):
        pass


class RagIndexerScopeTests(unittest.TestCase):
    def test_only_requested_category_is_indexed_from_full_snapshot(self):
        source = FakeSource()
        store = FakeStore()
        settings = Settings("http://source", "postgresql://db")

        summary = index_dataset(
            source,
            store,
            FakeEmbedder(),
            settings,
            categories=("Appliances",),
        )

        self.assertEqual(source.product_categories, ["Appliances"])
        self.assertEqual(source.review_categories, ["Appliances"])
        self.assertEqual([product.category for product in store.products], ["Appliances"])
        self.assertEqual(summary.counts.product_count, 1)
        self.assertEqual(summary.counts.category_counts.keys(), {"Appliances"})
        self.assertEqual(store.activated_counts["category_counts"].keys(), {"Appliances"})

    def test_unknown_category_fails_before_creating_a_run(self):
        source = FakeSource()
        store = FakeStore()

        with self.assertRaisesRegex(IndexingError, "invalid_category_scope"):
            index_dataset(
                source,
                store,
                FakeEmbedder(),
                Settings("http://source", "postgresql://db"),
                categories=("Books",),
            )

        self.assertEqual(store.begin_calls, 0)
        self.assertEqual(source.product_categories, [])

    def test_default_scope_keeps_all_snapshot_categories(self):
        source = FakeSource()
        store = FakeStore()

        summary = index_dataset(
            source,
            store,
            FakeEmbedder(),
            Settings("http://source", "postgresql://db"),
        )

        expected = ["Appliances", "Clothing_Shoes_and_Jewelry"]
        self.assertEqual(source.product_categories, expected)
        self.assertEqual(source.review_categories, expected)
        self.assertEqual(summary.counts.category_counts.keys(), set(expected))


if __name__ == "__main__":
    unittest.main()
