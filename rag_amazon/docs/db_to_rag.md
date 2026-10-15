# DB → RAG 규격 초안 v1

영두님 API 문서와 실제 응답을 기준으로 구현했습니다. 팀 합의 완료를 의미하지 않습니다. API 원본은 읽기 전용이고 RAG 산출물은 별도 로컬 파일입니다.

## API와 수집 snapshot

`db_to_rag_example.json`은 합성 상품 1개·리뷰 1개를 담은 규격 예시입니다. 수집 client가 원본 응답에 category와 버전·수집 시각만 감쌉니다.

```json
{
  "schema_version": "amazon-snapshot-v1",
  "dataset_version": "API가 반환한 버전 문자열",
  "source_kind": "REAL",
  "base_url": "https://example.invalid",
  "categories": ["Appliances"],
  "products": [{"category":"Appliances","record":{"parent_asin":"원본 ID","title":"원본 상품명"}}],
  "reviews": [{"category":"Appliances","record":{"review_key":"안정적 원본 리뷰 키","parent_asin":"원본 ID","text":"리뷰 원문"}}]
}
```

record는 API 원본 전체 객체입니다. API category와 metadata main_category는 구분합니다. `dataset_version`은 모든 페이지·health 응답에서 같아야 합니다. reviews는 선택한 상품만 조회하므로 연결 상품이 없는 리뷰는 정상 수집본에 들어가지 않습니다.

## 검색 문서

필수 9필드는 product_id/document_id/document_type/title/brand/category/price/text/source_id입니다.

- product_id = 원본 parent_asin. 내부 Commerce 상품 ID와 같다고 가정하지 않습니다.
- source_id = 상품은 parent_asin, 리뷰는 review_key.
- document_id = URL 인코딩한 `amazon:category:type:parent_asin:source_id`.
- category = API 조회 범주, 문서 ID/상품 연결은 category를 포함합니다.
- title/brand/price = 연결 상품 메타데이터. 리뷰 제목은 별도 review_title.
- text = 상품은 검색 필드 조합, 리뷰는 원본 text 그대로.
- currency=USD, price_basis=dataset_crawl_time.
- source_locator = snapshot JSON pointer (`/reviews/N/record` 등).
- source_hash = 원본 record canonical JSON SHA256.
- dataset_version/source_kind/source_ref/parent_asin/asin도 보존합니다.
- commerce_product_id/variant_id는 확인 전 null.

corpus[i]와 documents[i].text는 같고 tokenized_corpus[i]는 같은 문서의 토큰입니다. 원본 ID/근거 연결을 확인할 때 document_id와 source_locator/source_hash를 사용하세요.

## Commerce 매핑

별도 `[{category,parent_asin,commerce_product_id}]` JSON을 `--mapping`으로 전달합니다. 중복·빈 ID는 실패합니다. 예시 파일은 placeholder이므로 실제 매핑 확인 후 사용해야 합니다. 매핑을 썼으면 build 결과에 commerce_mapping.json도 보존되고 verify에 반영됩니다. variant 매핑은 아직 입력 계약에 포함되지 않습니다.

## 필수 확인 사항

영두님과 원본 범주·ID·version·review_key 안정성 확인. 홍빈님과 실제 Commerce product/variant 매핑 및 최신 가격 조회 경계 확인. 리뷰 수는 API의 평점별 선별 샘플이며 전체 고객후기 분포로 일반화하지 않습니다.
