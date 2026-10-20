-- Connect to database toss. Read only. Change product ID when needed.
BEGIN READ ONLY;
SELECT category,count(*) FROM test_items2.products GROUP BY category ORDER BY category;
SELECT id,name,category,specs_json->>'product_type' AS product_type FROM test_items2.products WHERE name ILIKE '%니플%' ORDER BY name;
SELECT * FROM test_items2.product_variants WHERE product_id='p-v4-o-0286' ORDER BY unit_price_won,id;
SELECT id,product_id,variant_id,source_kind,rating,body,written_at FROM test_items2.reviews WHERE product_id='p-v4-o-0286' ORDER BY written_at DESC,id LIMIT 10;
ROLLBACK;
