# Amazon Reviews RAG 구현 계획

> 구현 담당자는 계획 리뷰 후 선택된 방식에 따라 superpowers:executing-plans 또는 superpowers:subagent-driven-development를 사용합니다. 각 작업은 체크박스로 진행 상태를 기록합니다.

**목표:** 선별한 Amazon Reviews'23 상품·리뷰 스냅샷에서 하이브리드 검색을 수행하고, 출처를 검증할 수 있는 상품 후보와 근거를 반환합니다.

**구조:** 원본 데이터는 기존 amzdata 스키마에 보존하고 기존 HTTP API로 읽습니다. PostgreSQL 18.6의 별도 rag 스키마에 버전이 지정된 상품, 근거 청크, 임베딩, 색인 실행 상태를 저장합니다. pg_search BM25 검색과 pgvector cosine 검색을 독립적으로 실행한 뒤 RRF로 상품 순위를 결합합니다.

**기술 스택:** PostgreSQL 18.6, pgvector 0.8.7, ParadeDB pg_search 0.26.0, Python, FastAPI, Psycopg 3, HTTPX, FastEmbed, LangChain Core, LangChain Community.

**설계 문서:** docs/superpowers/specs/2026-10-14-amazon-reviews-rag-design.md

## 전역 제약

- 기존 Amazon Reviews API 경로와 응답 계약을 변경하지 않습니다.
- RAG 색인기는 HTTP API로 원본을 읽고 amzdata에 직접 접속하지 않습니다.
- RAG DB 계정은 rag 스키마에만 접근하며 amzdata 권한을 받지 않습니다.
- PostgreSQL은 18.6으로 유지하고 pgvector 0.8.7, pg_search 0.26.0을 고정합니다.
- pgvector를 먼저 설치하고 pg_search를 설치합니다. PostgreSQL의 shared_preload_libraries에 pg_search를 설정합니다.
- 색인 데이터에 원본 dataset_version, 임베딩 모델, chunker 버전을 기록합니다.
- 초기 임베딩 모델은 sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2, 384차원으로 사용합니다.
- 제목, 개별 feature/description, details의 키·값, 리뷰 원문을 의미 단위로 색인하며 서로 다른 상품이나 리뷰의 근거를 섞지 않습니다.
- evidence_text는 지정한 원본 필드에서 그대로 가져오고, 오프셋은 해당 문자열의 Unicode 문자 위치를 사용합니다.
- 초기 dense 검색은 정확 검색으로 시작합니다. 측정한 지연 시간이 요구사항에 미달할 때만 근사 벡터 인덱스를 추가합니다.
- 원본 가격에는 통화 정보가 없으므로 가격을 KRW로 간주하지 않습니다.
- user_id는 정규화·색인·응답에 포함하지 않습니다. 질문과 리뷰 본문은 로그에 남기지 않습니다.
- LLM 답변 생성, 질의 재작성, 자동 번역, 재랭커, 추천 정책은 구현 범위에 넣지 않습니다.

## 주요 검토 항목

- 페이지 조회 중 dataset_version이 바뀌면 색인을 중단하고 이전 활성 버전을 유지합니다. (작업 3, 5)
- 페이지 재조회나 색인 재실행에도 안정적인 청크 ID로 중복을 만들지 않습니다. (작업 4, 5)
- 선택 필드가 null 또는 빈 문자열이어도 해당 항목을 건너뛰고 전체 카테고리 적재를 계속합니다. (작업 4)
- 다국어 리뷰를 문장 경계에서 분할해도 오프셋이 evidence_text를 정확히 가리킵니다. (작업 4, 7)
- 출처가 사라지거나 상품과 연결되지 않는 색인 실패를 완료 상태로 노출하지 않고 내부 오류 정보를 반환하지 않습니다. (작업 5, 6, 7)

---

### 작업 1: PostgreSQL 18.6 검색 확장 이미지 구성

**파일:**
- 생성: deploy/amazon-reviews-postgres-rag.Dockerfile
- 수정: deploy/amazon-reviews-postgres.yml

**제공 인터페이스:**
- 기존 PostgreSQL 18.6 서버에 vector와 pg_search 확장 파일이 설치된 컨테이너 이미지를 제공합니다.
- 현재 Compose 서비스의 DB명, 데이터 볼륨, 포트 바인딩, healthcheck는 유지합니다.

- [ ] postgres:18.6을 기반으로 pgvector 0.8.7과 pg_search 0.26.0을 PostgreSQL 18용으로 빌드·설치합니다.
- [ ] vector 설치를 pg_search 설치보다 먼저 실행하고 필요한 런타임 라이브러리를 이미지에 포함합니다.
- [ ] Compose에서 pg_search를 shared_preload_libraries에 설정합니다.
- [ ] 기존 영구 볼륨과 127.0.0.1:5432 바인딩을 유지합니다.
- [ ] 확장 버전을 Dockerfile 또는 배포 문서에 고정해 이미지 빌드를 재현 가능하게 합니다.

**완료 기준:** 컨테이너가 PostgreSQL 18.6으로 실행되고 toss_rag에서 vector와 pg_search 확장을 생성할 수 있습니다.

### 작업 2: 격리된 RAG 스키마와 계정 구성

**파일:**
- 생성: src/toss_ads/rag/__init__.py
- 생성: src/toss_ads/rag/bootstrap.py
- 생성: src/toss_ads/rag/store.py
- 생성: deploy/amazon-reviews-rag.env.example

**제공 인터페이스:**
- bootstrap_database(admin_database_url: str, rag_password: str) -> None은 역할과 rag 스키마를 준비합니다.
- create_schema(connection: psycopg.Connection) -> None은 RAG 테이블과 인덱스를 생성합니다.
- RagStore(database_url: str)는 RAG 저장소를 제공합니다.
- RAG_DATABASE_URL은 RAG 런타임 연결에, AMZDATA_ADMIN_DATABASE_URL은 bootstrap에만 사용합니다.
- RagStore 메서드는 begin_index_run(dataset_version: str) -> str, upsert_products(products: Sequence[IndexedProduct]) -> None, upsert_chunks(chunks: Sequence[EvidenceChunk]) -> None, activate_dataset(run_id: str, counts: IndexCounts) -> None, fail_index_run(run_id: str, error_code: str, counts: IndexCounts) -> None, search_bm25(query: str, dataset_version: str, limit: int) -> list[RankedChunk], search_vector(vector: Sequence[float], dataset_version: str, limit: int) -> list[RankedChunk]로 정의합니다.

- [ ] toss_rag에 rag 스키마와 vector, pg_search 확장을 생성합니다.
- [ ] rag.indexed_products에 (dataset_version, category, product_id) 복합 기본 키, product_payload JSONB, nullable price_amount NUMERIC, price_currency TEXT를 둡니다.
- [ ] rag.evidence_chunks에 안정적인 chunk_id, 상품 참조, 출처 타입/ID/필드, 오프셋, evidence_text, embedding_text, source_metadata JSONB, vector(384), embedding_model, chunker_version를 둡니다.
- [ ] rag.index_runs에 run_id, dataset_version, status(building/active/superseded/failed), 건수, 시작/완료 시각, 안전한 오류 코드를 기록합니다. 부분 unique index로 active 실행은 하나만 허용하고, 활성 버전 전환은 단일 트랜잭션으로 처리합니다.
- [ ] dataset_version, category, product_id, source_type용 B-tree 인덱스와 embedding_text용 pg_search BM25 인덱스를 둡니다.
- [ ] RAG 로그인 역할에는 rag 스키마 권한만 주고 amzdata 권한은 주지 않습니다.
- [ ] 연결 주소와 비밀값은 환경 변수로만 전달하고 예시 파일에는 자리표시자만 둡니다. bootstrap에는 RAG_ROLE_PASSWORD를, 런타임에는 RAG_DATABASE_URL을 사용합니다.

**완료 기준:** bootstrap을 반복 실행해도 안전하며, RAG 계정으로 rag를 읽고 쓸 수 있고 amzdata는 조회할 수 없습니다.

### 작업 3: 설정, 타입, API 원본 클라이언트

**파일:**
- 생성: requirements-rag.txt
- 생성: src/toss_ads/rag/config.py
- 생성: src/toss_ads/rag/types.py
- 생성: src/toss_ads/rag/source.py

**제공 인터페이스:**
- EvidenceChunk은 chunk_id, dataset_version, category, product_id, source_type, source_id, source_field, start_offset, end_offset, evidence_text, embedding_text, source_metadata, embedding_model, chunker_version를 가집니다.
- SourceProduct는 category, parent_asin, dataset_version, payload를 가집니다. SourceReview는 category, review_key, parent_asin, 정수 rating, dataset_version, payload를 가집니다. IndexedProduct는 dataset_version, category, product_id, product_payload, price_amount, price_currency를 가집니다. RankedChunk는 chunk_id, product_id, category, source_type, source_id, source_field, evidence_text, source_metadata, 채널 순위, 거리를 가집니다. IndexCounts는 product_count, review_count, chunk_count, category_counts를, IndexSummary는 run_id, dataset_version, status, counts를 가집니다. 모두 types.py에 정의합니다.
- AmazonReviewsClient.list_categories() -> CategorySnapshot은 카테고리 목록과 dataset_version을 반환합니다.
- AmazonReviewsClient.iter_products(category: str) -> Iterator[SourceProduct]는 해당 카테고리의 상품 레코드를 순회합니다.
- AmazonReviewsClient.iter_reviews(category: str) -> Iterator[SourceReview]는 해당 카테고리의 리뷰 레코드를 순회합니다.
- 설정값은 AMAZON_REVIEWS_API_BASE_URL, RAG_DATABASE_URL, RAG_EMBEDDING_MODEL, FASTEMBED_CACHE_PATH에서 읽습니다.

- [ ] RAG 전용 requirements 파일에서 requirements-api.txt를 포함하고 HTTPX, FastEmbed, LangChain Core, LangChain Community 의존성을 추가합니다.
- [ ] 기존 API의 최대 limit 200에 맞춰 카테고리·상품·리뷰 페이지 조회를 구현합니다.
- [ ] 모든 페이지의 dataset_version을 확인하고 한 페이지라도 바뀌면 수집을 실패 처리합니다.
- [ ] 응답 envelope와 필수 식별자를 검증한 뒤 타입이 정해진 레코드로 반환합니다.
- [ ] user_id를 정규화 레코드에서 제외하고 로그에는 request_id, 상태, 소요 시간, 오류 코드만 기록합니다.

**완료 기준:** API를 통해 세 카테고리의 상품 30,000개와 리뷰 178,335개를 페이지 단위로 수집할 수 있고, 원본 DB 직접 연결이나 전체 payload 메모리 적재를 사용하지 않습니다.

### 작업 4: 재현 가능한 상품·리뷰 청킹

**파일:**
- 생성: src/toss_ads/rag/chunker.py

**제공 인터페이스:**
- build_product_chunks(product: dict[str, object], category: str, dataset_version: str) -> list[EvidenceChunk]
- build_review_chunks(review: dict[str, object], product_title: str, category: str, dataset_version: str) -> list[EvidenceChunk]

- [ ] 상품 제목, 비어 있지 않은 feature 각각, description 항목 각각, details의 키·값 각각을 상품 청크로 만듭니다.
- [ ] embedding_text에는 상품 제목과 관련 필드명을 포함하고 evidence_text에는 해당 원본 값만 둡니다.
- [ ] 리뷰는 text를 근거로 삼고 상품 제목과 리뷰 제목을 임베딩 문맥에 포함합니다. text가 비었고 title이 있으면 title을 근거 필드로 색인합니다.
- [ ] 짧은 리뷰 본문은 하나의 청크로 유지하고 모델 입력 한도를 넘는 경우에만 문장·문단 경계에서 나눕니다.
- [ ] chunk_id는 dataset_version, category, product_id, source_type, source_id, source_field, 오프셋, chunker_version을 SHA-256으로 해시해 생성합니다.
- [ ] null·빈 값은 건너뛰고 서로 다른 원본 레코드의 근거를 하나로 합치지 않습니다.

**완료 기준:** 같은 원본을 다시 처리하면 같은 chunk_id가 생성되고, source_field와 오프셋으로 잘라낸 문자열이 evidence_text와 일치합니다.

### 작업 5: 임베딩, 저장, 전체 버전 활성화

**파일:**
- 생성: src/toss_ads/rag/embeddings.py
- 생성: src/toss_ads/rag/indexer.py
- 생성: src/toss_ads/rag/__main__.py
- 수정: deploy/amazon-reviews-rag.env.example

**제공 인터페이스:**
- create_embedder(model_name: str, cache_path: str) -> FastEmbedEmbeddings
- index_dataset(client: AmazonReviewsClient, store: RagStore, embedder: Embeddings) -> IndexSummary
- 실행 명령: python -m toss_ads.rag index

- [ ] 설정된 다국어 모델을 로드하고 출력 벡터 차원이 384인지 확인합니다.
- [ ] API에서 카테고리별 상품·리뷰를 가져와 category와 parent_asin으로 연결하고 상품 payload를 indexed_products에 저장합니다.
- [ ] 제한된 배치 크기로 임베딩을 생성해 청크, 벡터, 모델명, chunker 버전을 evidence_chunks에 저장합니다.
- [ ] 색인 데이터는 dataset_version별로 분리해 실패한 실행이 현재 활성 버전을 덮지 않도록 합니다.
- [ ] 활성화 전에 원본 dataset_version을 다시 확인하고, 변경·API 실패·DB 실패 시 실행을 실패로 기록하고 이전 활성 버전을 유지합니다.
- [ ] 안정적인 chunk_id와 upsert로 같은 버전의 재실행을 멱등하게 처리합니다.
- [ ] 완료 시 dataset_version, 상품 수, 청크 수, 실행 상태를 출력하되 원문이나 비밀값은 출력하지 않습니다.

**완료 기준:** 완전한 단일 버전만 활성화되며, 동일 버전 재실행으로 중복 청크가 늘어나지 않습니다.

### 작업 6: 하이브리드 검색과 RAG API

**파일:**
- 생성: src/toss_ads/rag/retriever.py
- 생성: src/toss_ads/rag/api.py
- 생성: src/toss_ads/rag/schemas.py

**제공 인터페이스:**
- search(request: RagSearchRequest) -> RagSearchResponse
- POST /v1/rag/search는 승인된 Agent-to-RAG v0.1 요청·응답 구조를 사용합니다.
- RagSearchResponse의 status는 ok, no_results, low_relevance, error 중 하나입니다.
- RagSearchRequest는 request_id(선택), original_question, query, filters(price_min/price_max/currency), required_conditions, preferences, top_k를 포함합니다. RagSearchResponse는 request_id, status, dataset_version, applied_filters, unverified_conditions, items, error_code를 포함합니다. 각 item은 product_id, category, product_metadata, rrf_score, evidence를 포함하고 각 evidence는 chunk_id, source_type, source_id, source_field, source_version, evidence_text, source_metadata, offsets, BM25/vector/RRF 순위를 포함합니다.

- [ ] 요청 타입, 필수값, 가격 범위 순서, 가격이 있을 때 통화 제공 여부, top_k를 검증하고 요청 검증 실패는 error_code invalid_request로 반환합니다.
- [ ] 전달된 query를 임베딩하며 LLM 질의 재작성이나 번역은 호출하지 않습니다.
- [ ] BM25와 정확 cosine 검색을 각각 실행하고 채널별 후보 깊이는 20으로 시작합니다.
- [ ] 각 채널에서 상품별 최고 청크 순위를 사용하고, 독립 순위를 RRF로 결합합니다. RRF_K는 기본 60이며 설정값으로 조정할 수 있습니다.
- [ ] 서로 다른 상품을 최대 top_k개 반환하고 상품마다 근거를 최대 3개 포함하며 같은 리뷰에서 겹치는 청크는 제거합니다.
- [ ] 원문 근거, 출처 필드·오프셋·ID·dataset_version, 채널별 순위, RRF 순위를 반환합니다.
- [ ] 선호와 검증 불가능한 가격·기능 조건은 hard filter로 적용하지 않고 unverified_conditions에 반환합니다.
- [ ] 검증·DB·임베딩·타임아웃 오류를 안정된 오류 코드로 매핑하고 SQL, 자격 증명, 스택 트레이스는 응답에서 숨깁니다.
- [ ] original_question과 리뷰 본문은 로그에서 제외합니다.

**완료 기준:** 응답이 승인된 계약을 지키고 no_results, low_relevance, error를 구별하며 RRF 점수를 확률로 표시하지 않습니다.

### 작업 7: 검색 평가 데이터와 운영 문서

**파일:**
- 생성: evals/amazon_reviews_rag.jsonl
- 생성: src/toss_ads/rag/evaluate.py
- 생성: docs/amazon-reviews-rag.md
- 수정: data/amzdata/README.md

**제공 인터페이스:**
- 평가 레코드는 split, query, 관련 product_id, 관련 source_type/source_id를 포함합니다.
- 실행 명령: python -m toss_ads.rag.evaluate --split tuning

- [ ] 정확한 상품명, 원문 리뷰 표현, 한국어 질문과 영어 원문 간 의미 검색, 긍정·부정 근거, 무관 질문, 원본에 없는 질문을 포함한 tuning/holdout 질문을 만듭니다.
- [ ] 긍정 검색 사례는 현재 세 카테고리 스냅샷에 실제 존재하는 상품과 source ID만 사용합니다.
- [ ] 관련 source ID가 결과 상품 및 대표 근거에 포함되는지와 자료 없음 질문의 상태를 보고합니다.
- [ ] source_field[start_offset:end_offset]가 evidence_text와 일치하는지, 리뷰의 review_key·parent_asin·category가 결과 상품과 연결되는지 확인합니다.
- [ ] low_relevance 기준은 tuning 질문으로 정하고 holdout 결과를 별도로 보고합니다.
- [ ] PostgreSQL 18.6 확장 준비, 환경 변수, 색인·검색 실행, 버전 갱신, 응답 근거와 한계를 문서화합니다.
- [ ] 기존 API 계약을 변경하지 않고 RAG 운영 절차를 데이터 안내 문서에 연결합니다.

**완료 기준:** 운영자가 rag 스키마 준비, 특정 dataset_version 색인, 검색 서비스 실행, 샘플 요청, 근거·상태 해석을 문서만 보고 수행할 수 있습니다.
