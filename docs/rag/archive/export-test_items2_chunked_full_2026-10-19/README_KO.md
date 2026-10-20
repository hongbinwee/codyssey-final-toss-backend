# test_items2 청킹·임베딩 공유 자료

5432 서버의 test_items2 데이터와 해당 RAG 색인만 읽기 전용으로 내보냈습니다.

## 포함 데이터
- 상품: 1,500개 / 옵션: 1,917개 / 리뷰: 46,100개
- 실제 수집 REAL 리뷰: 41,523개 / 합성 SYNTHETIC 리뷰: 4,577개
- 청크: 114,106개 (상품·옵션 37,919개 / 리뷰 76,187개)
- 임베딩: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
- 청크마다 384차원 숫자 벡터 전체를 embedding 배열에 포함
- 최대 96토큰 청크
- 카테고리: beauty, fashion, food, living
- 프로필: test_items2
- run_id: e925490f-4f34-4c03-9248-eb9ebdfcde48

## 폴더 구조
shopping_brain_v6_1_common_dataset/   전달받은 원본 폴더/파일 4개 그대로
  data/products.json
  data/variants.json
  data/reviews.json
  README.md
database_exports/
  toss/test_items2/                 현재 원본 DB 스냅샷
    products.jsonl
    product_variants.jsonl
    reviews.jsonl
    schema.sql
  toss_rag/rag/                     test_items2 색인만 포함
    evidence_chunks.jsonl           청크 본문·출처·전체 임베딩 벡터
    indexed_products.jsonl          색인 당시 상품/옵션 메타데이터 스냅샷
    index_runs.jsonl
    index_profiles.jsonl
    quarantined_products.jsonl
    schema.sql
metadata/
  load_report.json
  index_report.json
  export_manifest.json
SHA256SUMS.txt

## 읽는 방법
JSONL은 UTF-8이며 한 줄에 JSON 객체 하나가 있습니다.
청크의 embedding은 생략하거나 요약하지 않은 길이 384의 숫자 배열입니다.
product_id는 toss.test_items2.products.id와 연결됩니다.
리뷰 청크의 source_id는 toss.test_items2.reviews.id와 연결됩니다.
source_metadata에 REAL/SYNTHETIC, 원본 테이블, variant_id 등의 근거가 보존되어 있습니다.
이미지는 URL만 포함합니다.
schema.sql은 구조만 포함하며 데이터는 JSONL에 별도로 있습니다.
RAG 스키마를 재생성하려면 호환되는 PostgreSQL과 pgvector/pg_search 확장이 필요합니다.
이 파일에는 DB 접속 인증정보, 모델 가중치, 기존 test_items의 청크가 포함되지 않습니다.
원본은 v6.1 CANDIDATE 자료이며 원본 README의 데이터 한계를 함께 확인하세요.
이 ZIP은 데이터 공유 자료이며 API의 기본 검색 대상을 변경하지 않습니다.

## 검증
상품/리뷰 ID 전체 일치, 참조 연결, 384차원 벡터, 출처별 본문 오프셋을 검증했습니다.
원본 폴더의 파일 내용은 전달받은 ZIP과 동일하게 보존했습니다.
SHA256SUMS.txt에는 이 체크섬 파일 자체를 제외한 모든 파일의 SHA-256이 있습니다.
