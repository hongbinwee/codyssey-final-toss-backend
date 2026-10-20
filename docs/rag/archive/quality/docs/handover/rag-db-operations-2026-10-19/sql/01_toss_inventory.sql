-- Connect to database toss. Read only.
BEGIN READ ONLY;
SELECT current_database(),current_user,current_schema(),current_setting('search_path');
SELECT table_schema,table_name FROM information_schema.tables WHERE table_schema IN ('public','test_earphones','test_items','test_items2') AND table_type='BASE TABLE' ORDER BY table_schema,table_name;
SELECT 'products' AS source,count(*) FROM test_items2.products UNION ALL SELECT 'variants',count(*) FROM test_items2.product_variants UNION ALL SELECT 'reviews',count(*) FROM test_items2.reviews;
ROLLBACK;
