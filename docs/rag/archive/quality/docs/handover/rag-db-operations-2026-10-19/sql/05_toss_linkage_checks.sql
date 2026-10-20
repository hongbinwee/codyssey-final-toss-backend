-- Connect to database toss. Read only. Validation examples, not a supplied pass result.
BEGIN READ ONLY;
SELECT count(*) AS orphan_variants FROM test_items2.product_variants v LEFT JOIN test_items2.products p ON p.id=v.product_id WHERE p.id IS NULL;
SELECT count(*) AS orphan_reviews FROM test_items2.reviews r LEFT JOIN test_items2.products p ON p.id=r.product_id WHERE p.id IS NULL;
SELECT count(*) AS mismatched_review_variants FROM test_items2.reviews r LEFT JOIN test_items2.product_variants v ON v.product_id=r.product_id AND v.id=r.variant_id WHERE r.variant_id IS NOT NULL AND v.id IS NULL;
SELECT source_kind,count(*) AS reviews,count(*) FILTER (WHERE variant_id IS NULL) AS null_variant_id FROM test_items2.reviews GROUP BY source_kind;
ROLLBACK;
