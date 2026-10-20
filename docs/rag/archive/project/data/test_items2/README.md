# test_items2 데이터 적재 및 색인

- 원본: shopping_brain_v6_1_review_refined_CANDIDATE.zip
- 원본 상품/옵션/리뷰 JSON은 source/ 아래에 전달받은 폴더 구조로 보존
- 원본 DB: 5432 → toss → test_items2
- products: 1,500개
- product_variants: 1,917개
- reviews: 46,100개 (REAL 41,523 / SYNTHETIC 4,577)
- reviews.source_option_label: 원본 옵션 표기를 보존한 추가 nullable TEXT 컬럼
- specs → specs_json, option_values → option_values_json, spec_overrides → spec_overrides_json
- 원본 ID, 본문, 출처, 날짜와 옵션 연결을 보존했으며 DB 적재 결과와 원본을 대조

## RAG 저장 위치

- 5432 → toss_rag → rag
- 프로필: test_items2
- run_id: e925490f-4f34-4c03-9248-eb9ebdfcde48
- dataset_version: test_items2:v6.1-review-refined:sha256=94681a28271ca9b1:products=1500:reviews=46100
- 상태: active (test_items2 프로필 내부 활성화)
- 모델: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
- 벡터 차원: 384
- 청크 최대 토큰: 96
- 청크 합계: 114,106 (상품·옵션 37,919 / 리뷰 76,187)
- 범주: beauty, fashion, food, living
- source_metadata로 원본 DB/테이블, 상품·리뷰·옵션 ID, REAL/SYNTHETIC을 추적

## 검증 및 API 연결

각 범주에서 BM25 및 벡터 검색 결과를 확인했습니다.
상품 ID 1,500개 및 리뷰 source_id 46,100개를 확인하고 벡터 차원/본문 오프셋 오류가 0개임을 확인했습니다.
기존 all_products 프로필은 현재 API의 기본 대상으로 남아 있습니다.
현재 API에는 기존 test_items 데이터셋을 지정한 검증 로직이 있으므로,
test_items2를 HTTP API로 제공하려면 해당 프로필과 데이터셋을 연결하는 별도 변경이 필요합니다.

load_report.json은 적재, index_report.json은 청킹·임베딩·검색 확인 결과입니다.
