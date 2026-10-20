# test_items 전체 데이터 묶음

5432의 toss-postgres에서 test_items 데이터와 현재 활성 RAG 색인을 읽기 전용으로 내보냈습니다.

## 폴더 구조

shopping_brain_v4_demo_final/       수신한 원본 ZIP의 폴더/파일 24개, 내용 그대로
  db/seeds/                       원본 상품/리뷰 JSON
  rag/                            원본 RAG용 상품/리뷰/옵션 문서
  evidence/, preview/, qa/, ...    원본 근거/미리보기/품질 자료 및 스크립트

database_exports/
  toss/test_items/
    products.jsonl, products.csv
    product_variants.jsonl, product_variants.csv
    reviews.jsonl, reviews.csv
    schema.sql                    test_items 스키마의 테이블/키/제약조건 정의
  toss_rag/rag/
    index_runs.jsonl
    index_profiles.jsonl
    indexed_products.jsonl        RAG 색인의 상품 스냅샷
    evidence_chunks.jsonl         청크 본문, 출처, 메타데이터, 전체 임베딩 벡터
    quarantined_products.jsonl
    schema.sql                    rag 스키마의 테이블/키/인덱스 정의

export_metadata.json               내보낸 시각, 모델, 색인 버전, 수량, 검증 결과
SHA256SUMS.txt                      파일별 SHA-256 해시

## 수량과 형식

- 상품 180개 / 옵션 180개 / 리뷰 4,737개
- 색인 상품 180개 / 청크 6,741개
- 임베딩: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2, 청크당 384차원 전체 숫자 배열
- 활성 프로필: all_products
- 색인 run_id: 49537fff-9b05-4b9c-aed1-c4e690a4f689
- dataset_version: test_items:sha256=4e9924492dcb536e:products=180:reviews=4737
- JSONL: UTF-8, 한 줄에 레코드 하나. embedding은 JSON 숫자 배열입니다.
- CSV: 한국어 Excel 열기를 위해 UTF-8 BOM을 포함합니다. 배열/객체는 셀 안에 JSON으로 보존합니다.
- schema.sql: 구조만 포함합니다. 데이터는 JSONL/CSV 파일에 별도로 있습니다.
- rag 스키마 재생성에는 원래 환경의 pgvector/pg_search 확장과 호환되는 PostgreSQL이 필요합니다.

## 데이터 구분

원본 폴더는 전달받은 입력 파일을 그대로 보존한 것입니다.
database_exports는 현재 DB 스냅샷이므로 원본 입력 파일과 내용이 다를 수 있습니다.
현재 test_items의 리뷰 4,737개는 모두 합성(SYNTHETIC)이며 가격·재고·옵션은 모의 데이터입니다.
이미지 주소는 원본 URL로 보존했습니다.

DB 상품 ID 전체와 RAG 상품 ID 전체, DB 리뷰 ID 전체와 RAG 리뷰 source_id 전체의 일치를 확인했습니다.
각 청크에 384차원 벡터가 모두 들어 있는지도 확인했습니다.
