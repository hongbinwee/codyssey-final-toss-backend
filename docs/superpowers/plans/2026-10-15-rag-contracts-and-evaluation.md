# RAG 공동 규격과 원본 근거 검증 구현 계획

> 구현 방식: 사용자에게 승인받은 기준으로 이 채팅에서 직접 실행합니다. superpowers:executing-plans를 적용합니다.

**목표:** DB→RAG와 RAG→Agent 규격을 파일로 제공하고, 실제 API 출처에 연결된 공통 질문과 재실행 가능한 검증 도구를 완성합니다.

**구조:** 기존 `codex/amazon-reviews-rag` 구현은 다른 채팅 소유이므로 읽기 전용으로 검토합니다. Backend 저장소의 별도 `codex/rag-contracts-validation` 브랜치에 JSON Schema, 원본 샘플, 질문 세트, 검증 CLI를 추가합니다. 운영 DB·API와 기존 RAG 작업 디렉터리는 변경하지 않습니다.

**기술 스택:** Python 3, JSON Schema 2020-12, jsonschema, HTTPX, unittest.

**설계:** `docs/superpowers/specs/2026-10-14-amazon-reviews-rag-design.md`, 현재 채팅에서 승인한 BM25 + FastEmbed + LangChain / RRF 기준.

## 전역 제약

- 기본 검색은 BM25 + FastEmbed 하이브리드, LangChain 포함, RRF k=60, 채널별 초기 후보 20개, top_k 기본 10·최대 20, 상품별 최대 근거 3개입니다.
- 원본 상품 ID parent_asin과 리뷰 review_key, category, dataset_version을 보존합니다.
- user_id를 샘플·규격·응답에 포함하지 않습니다.
- 출력 예시의 검색 순위는 형식 설명용이며 실제 검색 성능으로 보고하지 않습니다.
- 실제 질문별 관련 원본은 API에서 대조합니다. tuning과 holdout은 상품 단위로 분리합니다.
- 팀의 개별 질문 판정과 타 담당자의 규격 승인은 완료했다고 간주하지 않습니다.

## 주요 검토 항목

- 올바른 JSON 형식이어도 상품/리뷰 연결 또는 원본 버전이 다르면 실패합니다.
- 원문 오프셋과 근거 문장이 다르면 실패합니다.
- API 페이지 도중 버전이 바뀌거나 리뷰가 다른 상품에 속하면 실패합니다.
- 검색 HTTP 호출이 성공해도 관련 출처를 놓치면 품질 통과로 세지 않습니다.
- 빈 검색 결과·낮은 관련성·오류 응답은 별도 상태로 유지합니다.

### 작업 1: 입출력 계약과 검사기

파일: `contracts/amazon-reviews-rag/v0.1/*`, `scripts/rag_contracts.py`, `tests/test_rag_contracts.py`.

- [x] 잘못된 요청, 응답 상태, 상품·버전·오프셋 불일치, 개인정보 노출을 잡는 테스트를 먼저 작성하고 실패를 확인합니다.
- [x] request/source/response JSON Schema와 실제 출처를 사용한 완성된 형식 예시를 만듭니다.
- [x] `validate(kind, payload)`로 구조와 상호 필드 관계를 검사합니다.
- [x] 계약 테스트를 실행합니다.

### 작업 2: 실제 원본 기반 공통 질문

파일: `evals/amazon_reviews_rag_cases.json`, `evals/fixtures/amazon_reviews_rag_sources.json`.

- [x] 실제 API에서 10개 상품과 연결 리뷰를 캡처하고 user_id가 없는지 확인합니다.
- [x] 상품/리뷰 각 1문항씩 총 20문항을 만들고 관련 상품·출처·필드·근거를 지정합니다.
- [x] 상품 단위로 tuning 12문항 / holdout 8문항을 분리합니다.
- [x] `verify_case_sources`로 모든 ID와 원문 근거를 대조합니다. 음성 사례는 팀 판정 전 별도 제안으로 표시합니다.

### 작업 3: 실행 도구와 진행 근거

파일: `scripts/rag_contracts.py`, `docs/amazon-reviews-rag-contracts.md`, `docs/rag-progress-2026-10-15.md`.

- [x] 원본 전용 검증과 RAG API가 준비된 뒤 사용할 검색 평가 모드를 제공합니다.
- [x] 검색 평가에서 원본 버전·근거 일치, 상품/출처 적중, 상태 적중을 보고하고 실패 시 종료 코드 1을 반환합니다.
- [x] 기존 RAG 코드의 검증 가능 상태와 실행상 결함을 읽기 전용으로 검토합니다.
- [x] 전체 테스트와 실제 API 출처 검증을 실행하고 수치·제한을 문서에 기록합니다.

## 실행 기록

- 기본 기존 테스트: unittest 5/5 통과.
- 기존 RAG 코드: 다른 채팅 소유 작업 트리에서 발견. main에 통합되지 않은 초안으로 확인.
- 격리 실행 환경: `/tmp/toss-rag-contracts-venv`. 운영 API Python 환경을 변경하지 않음.
- RED: 계약 검사기 미구현으로 11개 검증 테스트 실패를 확인함.
- GREEN: 기존 5개 + 신규 15개 = 20개 통과. 예시 6개 구조 검증 및 live API 원본 20/20 일치.
- Ruling: 다른 채팅 소유 RAG 구현을 수정하는 대신 독립 규격/평가 브랜치를 작성함. 원본 구현의 실행 결함은 진행 문서에 기록. 기존 브랜치가 이번 계약을 통합해야 하는 비용이 남음.
- Ruling: 자료 없음 질문은 원본 자료 범위·관련성의 팀 판정 전까지 골든셋에 넣지 않음. 음성 사례까지 포함한 low_relevance 교정은 별도 실행이 필요함.
- Review fix: 원본과 다른 상품/리뷰 메타데이터 통과, 중복 페이지로 인한 누락 리뷰, HTTP 실패 시 시도 상태·부분 결과 누락, 잘못된 JSON 최상위 형식을 회귀 테스트로 재현하고 수정함.
- Final GREEN in source checkout: 기존 5개 + 신규 20개 = 25개 통과. Backend 포팅 후에는 계약/출처 테스트 21/21, 예시 6/6, live source 20/20을 별도 확인함. 검색 API 경로는 MockTransport이며 실제 RAG 검색 POST는 실행하지 않음.
- Ruling: 공통 규칙에 따라 산출물을 Backend 저장소의 `codex/rag-contracts-validation` 브랜치로 포팅함. DB·Agent 담당자 확인 전까지 양방향 계약은 제안 상태이며 승인으로 표시하지 않음.
- Privacy minimization: 공개 fixture에서 작성자 프로필, 상품/리뷰 이미지와 영상, 질문에서 사용하지 않는 원본 필드를 제외함. 필수 source identifier `review_key`와 평가에 쓰이는 원문 근거는 보존함. 직접 식별자·연락처·credential pattern 검사는 0건.
