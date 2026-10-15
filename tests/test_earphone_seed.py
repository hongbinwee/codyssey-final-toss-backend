import unittest

from scripts.seed_earphones_test import (
    generate_products,
    generate_reviews,
    render_seed_sql,
)


class EarphoneSeedTest(unittest.TestCase):
    def test_generates_fifty_unique_earphone_products(self):
        products = generate_products(count=50, seed=20261015)

        self.assertEqual(len(products), 50)
        self.assertEqual(len({product["id"] for product in products}), 50)
        self.assertEqual({product["category"] for product in products}, {"earphones"})
        self.assertTrue(all(product["name"] for product in products))
        self.assertTrue(all(isinstance(product["specs_json"], dict) for product in products))

    def test_generates_twenty_varied_reviews_per_product(self):
        products = generate_products(count=50, seed=20261015)
        reviews = generate_reviews(products, reviews_per_product=20, seed=20261015)

        self.assertEqual(len(reviews), 1000)
        self.assertEqual(len({review["id"] for review in reviews}), 1000)

        for product in products:
            product_reviews = [review for review in reviews if review["product_id"] == product["id"]]
            self.assertEqual(len(product_reviews), 20)
            self.assertEqual({review["rating"] for review in product_reviews}, {1, 2, 3, 4, 5})
            self.assertTrue(all(review["source_kind"] == "SYNTHETIC" for review in product_reviews))

    def test_renders_only_test_schema_and_preserves_relationships(self):
        sql = render_seed_sql(schema="test_earphones", product_count=50, reviews_per_product=20)

        self.assertIn("DROP SCHEMA IF EXISTS test_earphones CASCADE", sql)
        self.assertIn("CREATE SCHEMA test_earphones", sql)
        self.assertIn("CREATE TABLE test_earphones.products", sql)
        self.assertIn("CREATE TABLE test_earphones.product_variants", sql)
        self.assertIn("CREATE TABLE test_earphones.reviews", sql)
        self.assertIn("REFERENCES test_earphones.products", sql)
        self.assertIn("REFERENCES test_earphones.product_variants", sql)
        self.assertNotIn("INSERT INTO public.products", sql)
        self.assertNotIn("INSERT INTO public.reviews", sql)


if __name__ == "__main__":
    unittest.main()
