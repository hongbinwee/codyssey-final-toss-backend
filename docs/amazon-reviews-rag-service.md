# Amazon Reviews RAG 서비스

이 Backend 브랜치는 Agent의 검색 요청에 대해 상품 후보와 원본 근거를 반환합니다. 답변 생성은 하지 않습니다.

전체 흐름은 [RAG 전체 방향](rag-overall-direction.md)을 참고하세요. 이 문서는 설치와 실행 방법을 설명합니다.

## 구성

- 원본: 기존 Amazon Reviews API (`/v1/categories`, category별 products/reviews 페이지)
- 검색 DB: `toss_rag` 내 `rag` 스키마, pgvector 0.8.7과 ParadeDB pg_search 0.26.0
- 어휘 검색: ParadeDB BM25
- 의미 검색: LangChain `FastEmbedEmbeddings`, `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384차원)
- 결합: 상품별 채널 최고 순위를 RRF k=60으로 결합
- API: FastAPI `POST /v1/rag/search`

FastEmbed는 이 모델의 입력 길이를 128 tokens로 안내합니다. 기본 청크 상한은 같은 tokenizer로 계산한 96 tokens이며 제목·필드 문맥도 이 수에 포함됩니다. 모델/라이브러리 업데이트 시 입력 길이를 다시 확인하세요. [FastEmbed 지원 모델](https://qdrant.github.io/fastembed/examples/Supported_Models/), [FastEmbed tokenizer API](https://github.com/qdrant/fastembed/blob/main/fastembed/text/text_embedding.py)

## DB 준비

기존 PostgreSQL 18.6 데이터 볼륨을 유지하면서 Compose가 `deploy/amazon-reviews-postgres-rag.Dockerfile`의 고정 이미지를 빌드합니다. ParadeDB `pg_search` 0.26.0과 pgvector 0.8.7을 제공하며, `shared_preload_libraries`에는 `pg_search,pg_cron`을 설정합니다. `pg_cron`은 ParadeDB 이미지의 초기화 절차가 필요로 합니다. DB 확장 및 RAG 스키마는 아래 bootstrap으로 만듭니다.

관리자 자격 증명은 bootstrap 때만 사용합니다.

```bash
python3 -m venv .venv-rag
.venv-rag/bin/pip install -r requirements-rag-service.txt
set -a
. deploy/amazon-reviews-rag-bootstrap.env
set +a
PYTHONPATH=src .venv-rag/bin/python -m toss_ads.rag.bootstrap
```

Bootstrap은 `toss_rag` 데이터베이스에서 vector 0.8.7과 pg_search 0.26.0을 확인하고, `rag` 스키마와 `amazon_rag` 실행 계정을 준비합니다. 실행 계정은 `rag` 스키마에만 읽기/쓰기 권한을 받습니다. 연결 URL과 비밀번호는 템플릿 값으로 남아 있으니 실제 값은 로컬의 비공개 환경 파일이나 비밀 저장소에서 공급하세요.

## 색인 및 실행

별도 런타임 환경에 `deploy/amazon-reviews-rag-runtime.env.example`의 값을 준비합니다. 실제 source API 주소와 `amazon_rag` 연결 URL을 설정한 뒤:

```bash
set -a
. /path/to/amazon-reviews-rag-runtime.env
set +a
PYTHONPATH=src .venv-rag/bin/python -m toss_ads.rag index
PYTHONPATH=src .venv-rag/bin/python -m toss_ads.rag serve --host 0.0.0.0 --port 8001
```

`index`는 category 전체의 상품·리뷰 페이지를 읽습니다. 각 페이지의 `dataset_version`, 예상 건수, 리뷰의 `parent_asin` 연결을 확인하고 64개 청크 단위로 임베딩합니다. `main_category=Books`, 다른 알려진 최상위 상품군, 또는 ISBN/제본 정보처럼 명시적인 충돌 신호가 있는 상품은 `rag.quarantined_products`에 `pending_review`로 기록하고 상품·리뷰 모두 검색 색인에서 제외합니다. 실행 건수에는 원본 읽기, 실제 색인, 격리를 카테고리별로 따로 남깁니다. 완료 전 애플리케이션 오류가 나면 해당 실행은 `failed`로 기록되고 이전 활성 색인은 유지됩니다. 기본 재실행은 새 `run_id`를 사용합니다. 프로세스가 강제 종료돼 `building`으로 남은 실행은 해당 ID를 지정해 이어갈 수 있고, 이미 DB에 저장된 청크는 다시 임베딩하지 않습니다.

```bash
PYTHONPATH=src .venv-rag/bin/python -m toss_ads.rag index --resume-run-id <BUILDING_RUN_ID>
```

현재 샘플은 세 원본 카테고리에서 각각 1만 상품을 뽑았으며 Books 카테고리를 따로 수집하지 않았습니다. 의류 원본 파일 안에 `main_category=Books`인 `The Would Be Queen` 상품이 포함된 데이터 분류 충돌이 있었고, 새 색인 정책은 이를 격리합니다. Books로 자동 이동하지 않습니다.

격리 결과는 다음 조회로 확인할 수 있습니다.

```sql
SELECT run_id, category, product_id, reason_code, policy_version,
       main_category, categories, type_signals, review_status
FROM rag.quarantined_products
ORDER BY created_at DESC, category, product_id;
```

실제 서비스가 사용하는 DB URL은 `RAG_DATABASE_URL`뿐입니다. Admin URL과 `RAG_ROLE_PASSWORD`는 bootstrap 환경에만 둡니다. FastEmbed 모델은 `FASTEMBED_CACHE_PATH`에 내려받습니다.

## Agent 검색 계약

카테고리 필터를 추가한 RAG 입출력 제안은 [`contracts/amazon-reviews-rag/v0.2/`](../contracts/amazon-reviews-rag/v0.2/)에 있습니다. Agent 최종 수용 전까지 공동 계약 승인 상태는 아닙니다.

요청의 `query`로 BM25와 FastEmbed 검색을 실행합니다. `original_question`은 보존되지만 재작성·번역에 사용하지 않습니다. `category`가 있으면 원본 API 카테고리 키와 정확히 일치해야 하며, BM25·벡터 SQL 모두에서 `LIMIT` 전에 하드 필터로 적용합니다. `category`를 생략하면 전체 활성 색인에서 검색합니다. 지원하지 않는 카테고리는 검색을 넓히지 않고 `unsupported_category`와 현재 `supported_categories`를 반환합니다. 후보 기본 깊이는 채널별 20개, `top_k` 기본 10·최대 20, 상품별 근거 최대 3개입니다. 출처 필드는 JSON Pointer이고 오프셋은 원본 Unicode 문자열 기준입니다.

가격, 통화, 필수 조건, 선호는 현재 hard filter로 적용되지 않습니다. 응답의 `unverified_conditions`를 Agent가 표시해야 합니다. `RAG_MIN_RRF_SCORE`는 기본 미설정이며, tuning/holdout 판정 없이 설정하지 않습니다. 상태는 `ok`, `no_results`, `low_relevance`, `error`로 구분됩니다.

```json
{
  "request_id": "agent-req-001",
  "original_question": "리눅스에서 쓸 수 있는 센서 리뷰를 찾아줘",
  "query": "Linux compatible sensor review",
  "category": "Appliances",
  "filters": {},
  "required_conditions": [],
  "preferences": [],
  "top_k": 10
}
```

이 샘플에서 `category`는 `Appliances`, `Clothing_Shoes_and_Jewelry`, `Grocery_and_Gourmet_Food` 중 하나를 사용할 수 있습니다. `Books` 요청은 색인에 Books가 없으므로 HTTP 422 `unsupported_category`로 끝납니다.

검색 응답의 `rrf_score`는 정답 확률이 아닙니다. `evidence_text`, `source_field`, 오프셋, `source_id`, `source_version`을 함께 사용해 답변의 근거를 확인하세요. DB 검색 SQL은 parameterized query를 사용하며 로그에는 질문과 리뷰 본문을 남기지 않습니다.

LangChain Core 호출이 필요한 구성에서는 `HybridRagRetriever.invoke(query)`가 `Document` 목록을 반환합니다. 각 Document의 `page_content`는 원문 근거이고 `metadata`에 상품·출처·순위가 들어갑니다.

## 운영 전 확인

- ParadeDB의 현재 SQL 경계는 [full-text search 문서](https://www.paradedb.com/blog/hybrid-search-in-postgresql-the-missing-manual)와 [검색 인덱스 환경 문서](https://www.paradedb.com/docs/documentation/getting-started/environment)를 참고합니다. 이 구현은 `|||`, `pdb.score`, `USING paradedb`를 사용합니다.
- 최초 전체 색인 시간과 DB 저장량은 실제 실행으로 측정해야 합니다.
- 한국어 질문과 영어 원문 회수율은 현재 검증되지 않았습니다. FastEmbed가 의미 검색을 보완하지만 품질은 골든 질문으로 평가해야 합니다.
- 가격 통화와 Agent의 JSON Pointer 소비 여부는 담당자 확인이 남아 있습니다.
- 색인 완료, 실제 검색 적중률, 임계값은 이 문서 작성만으로 검증된 것으로 보지 않습니다.
