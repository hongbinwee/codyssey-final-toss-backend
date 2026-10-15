# RAG 규격·공통 질문과 검증 실행

BM25 + FastEmbed 하이브리드, LangChain, 상품 단위 RRF 결합의 입출력 계약은 `contracts/amazon-reviews-rag/v0.1/`에 있습니다. 입력/응답 JSON Schema 3개와 실제 출처를 사용한 완성된 예시 6개를 제공합니다.

이 계약은 `codex/rag-contracts-validation` 브랜치에서 검토할 제안입니다. DB·Agent 담당자의 합의 기록은 아직 없으며, 프론트/백엔드 경계 규격도 이 작업의 범위에 포함하지 않았습니다. [공통 작업 규칙](common-work-rules.md)을 따릅니다.

## 검증 환경과 실행

기존 운영 API 환경에 패키지를 추가할 필요 없이 별도 환경을 사용할 수 있습니다.

```bash
python3 -m venv .venv-contracts
.venv-contracts/bin/python -m pip install -r requirements-rag-contracts.txt
.venv-contracts/bin/python scripts/rag_contracts.py --mode examples
.venv-contracts/bin/python scripts/rag_contracts.py --mode sources
```

현재 원본 API와 다시 대조하려면 다음 명령을 사용합니다.

```bash
.venv-contracts/bin/python scripts/rag_contracts.py --mode sources \
  --api-base-url "$AMAZON_REVIEWS_API_BASE_URL" \
  --output reports/rag-contracts/source-validation.json
```

이 모드는 원본 API만 호출합니다. 검색을 실행하지 않으며 `search_executed: false`로 보고합니다. 시작/종료 healthz와 모든 리뷰 페이지의 dataset_version이 골든 자료와 같아야 합니다. 리뷰의 parent_asin과 상품 ID, 원본 source_field의 오프셋·문자열을 대조하며 누락 페이지나 버전 변경은 실패로 처리합니다.

검색 모드의 `search_executed`는 검색 POST를 한 번 이상 시도했다는 뜻입니다. `search_attempts`는 시도 횟수이며, 검색 요청이 실패하면 앞서 완료된 질문 결과와 실패 상태를 보고서에 보존합니다.

## 질문 세트

- `evals/amazon_reviews_rag_cases.json`: 10개 상품에 대해 상품 필드 질문 10개와 리뷰 질문 10개. tuning 12문항·holdout 8문항이며 두 split에 같은 상품이 없습니다.
- `evals/fixtures/amazon_reviews_rag_sources.json`: 실제 API와 대조한 상품 10개·리뷰 10개의 최소 출처 스냅샷. 질문에 쓰인 상품 필드와 선택된 리뷰만 남겼고, 작성자 프로필·이미지·영상 메타데이터를 제외했습니다. `user_id`, 이메일·전화번호 같은 직접 연락처 필드는 없습니다. `review_key`는 원본 근거 연결에 필요한 64자리 해시 식별자입니다.
- `evals/amazon_reviews_rag_negative_proposals.json`: 자료 없음·저관련성 질문 3개 초안. 해당 질문은 팀의 자료 범위·관련성 판정 전까지 골든 평가에 포함하지 않습니다.

긍정 질문도 관련 원본의 존재와 근거 문자열을 확인한 후보입니다. 사람이 판정한 완전한 정답 집합이라고 주장하지 않습니다. annotation_status가 `source_verified_pending_team_review`이며 팀이 질문별 관련성을 검토해야 합니다. 현재 승인된 RAG 설계대로 긍정·부정 리뷰 근거를 포함하며 추천 정책의 별점 필터는 적용하지 않습니다.

## 검색 API 준비 후 평가

```bash
.venv-contracts/bin/python scripts/rag_contracts.py --mode search \
  --split tuning \
  --api-base-url "$AMAZON_REVIEWS_API_BASE_URL" \
  --rag-base-url "$RAG_SEARCH_API_BASE_URL" \
  --output reports/rag-contracts/search-tuning.json
```

검색 평가 모드는 매 질문마다 top_k=10으로 `/v1/rag/search`를 호출합니다. 기대 상품 적중, 기대 출처와 원문 범위 포함 여부, 상태 일치, 반환된 모든 근거의 원본 일치를 집계합니다. 기대 상품 이외의 후보도 원본 API에서 조회하여 검증합니다. 하나의 관련 상품·출처를 찾으면 그 문항의 hit로 셉니다. 다중 근거가 모두 필요한 질의의 recall을 측정하는 도구는 아닙니다.

HTTP 200만으로 성공 처리하지 않습니다. 계약 불일치, 원문 근거 불일치, 기대 출처 미검출은 passed=false와 종료 코드 1을 반환합니다. 개별 결과와 합계는 JSON 보고서에 남습니다. 실패 보고서에 원본 본문·연결 비밀값·스택 트레이스는 넣지 않습니다.

## 자동 검사

```bash
PYTHONPATH=src:. .venv-contracts/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

검색 HTTP 동작 테스트는 `httpx.MockTransport`로 실행하며 실제 RAG 서비스 검색을 대신하지 않습니다. Backend 브랜치 기준 자동 테스트는 21개입니다. 공개 샘플 점검에서 작성자 프로필·미디어 필드를 제거했고, 텍스트의 이메일·전화번호·일반적인 credential 패턴은 검출되지 않았습니다.

규격 예시는 실제 검색 성능의 증거가 아닙니다. low_relevance 임계값 교정, 음성 질문 승인, 전체 데이터 색인, 응답 시간 측정은 검색 서비스가 준비된 뒤 진행합니다.
