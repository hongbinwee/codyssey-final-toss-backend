# API·Agent 연동과 남은 과제

[목차](README.md) · [현재 검색 구성](current-system.md)

## 1. search_rag와 search_products

| 이름 | 담당 범위 | 검색 근거 |
|---|---|---|
| `search_rag` | AI 쇼핑 추천의 상품 후보·리뷰 근거 검색 | 활성 RAG run의 청크와 임베딩, BM25·벡터 검색 |
| `search_products` / Commerce `searchProducts` | 일반 상품 목록·카탈로그 탐색, 기존 Commerce 도구/설계에 등장 | 구현에 따라 원본 카탈로그/SQL 검색. 이름만으로 RAG 경유를 보장하지 않음 |
| `POST /v1/rag/search` | Python RAG 서비스의 HTTP 검색 계약 | 실제 `5432/toss_rag`와 옵션 조회 `5432/toss` |

최신으로 발견한 Commerce 감사/결정 문서는 AI 추천 도구를 `search_rag` 단일 경로로 적고 있다. 오래된 `CORE_TASK_SCOPE`, `DATA_TOOL_DESIGN`, 화면 기준 문서에는 `search_products`가 남아 있다. 도구명 선택·등록·실제 서버의 어댑터 경로 문제와 LangChain 적용 여부를 혼동하지 않는다.

`search_rag`라는 도구명도 단독 증거가 아니다. Brain이 local RAG, 예전 서버, 다른 프로필을 호출하면 Python API의 최신 수정이 반영되지 않는다. 응답의 `profile_name`, `dataset_version`, `search_context`, 요청 ID를 실제 네트워크 경로와 함께 확인해야 한다.

근거: [Commerce 감사 기록](archive/commerce-storefront/docs/COMMERCE_AUDIT.md), [구현 결정](archive/commerce-storefront/docs/IMPLEMENTATION_DECISIONS.md), [과거 도구 설계](archive/commerce-storefront/DATA_TOOL_DESIGN.md).

## 2. 현재 RAG HTTP 요청

아래는 사용 예시이며 이번 문서 작업에서 실행한 품질 테스트 결과가 아니다.

```http
POST /v1/rag/search
Content-Type: application/json
```

```json
{
  "request_id": "rag-doc-example-001",
  "profile": "test_items2",
  "original_question": "통학용으로 5만원 이하 백팩을 찾아줘. 후기도 보고 싶어",
  "query": "통학용 백팩",
  "category": "fashion",
  "product_type": "backpack",
  "filters": {"price_max": 50000, "currency": "KRW", "in_stock": true},
  "required_conditions": [],
  "preferences": ["통학용"],
  "top_k": 5
}
```

요청 원문·검색어는 필수다. `profile` 생략 시 현재 기본값은 test_items2다. `category`를 생략하면 해당 프로필의 네 범주가 검색 대상이다. 등록되지 않은 상품 유형이나 필드를 임의로 보내지 않는다.

가격은 `filters.price_min`, `price_max`, `currency`로 보낸다. `max_price` 같은 미등록 최상위 필드는 현재 계약과 다르다. 가격 제한과 재고는 같은 옵션에서 확인하며, **배송비·쿠폰·수량·총 결제액** 필터는 이 검색 API에 구현되어 있지 않다.

전체 계약: [API 가이드](archive/quality/docs/api/rag-api-guide-2026-10-19.md), [PDF](archive/quality/docs/reports/rag-api-guide-2026-10-19.pdf), [요청 JSON Schema](../../contracts/product-rag/v0.3/request.schema.json), [Postman collection](archive/quality/docs/api/rag-api.postman_collection.json).

## 3. 응답에서 확인할 것

| 항목 | 소비 측 처리 |
|---|---|
| HTTP 상태 + `status` + `error_code` | 오류·미준비·저관련성·결과 없음을 구분. 오류 응답을 빈 성공으로 취급하지 않음 |
| `profile_name`, `dataset_version` | 의도한 최신 데이터인지 확인 |
| `search_context` | 유형 판정, 관련성 버전, 적격 후보 수, 빈 결과 사유 확인 |
| `applied_filters` | 서버가 실제 적용했다고 보고한 조건 |
| `unverified_conditions` | 충족이 입증되지 않은 요구. `ok`여도 모든 필수 조건 통과가 아님 |
| `items[].commerce` | 선택 옵션 ID·단가·재고·조회 시각·데이터 근거 |
| `items[].evidence` | 실제 인용한 청크/리뷰 ID, 원문, source_kind, 위치 |
| `items[].ranking` | 정렬/관련성 검사 설명. 확률·정답 보장으로 표시하지 않음 |

과거 `/v1/catalog/test-items` 목록과 리뷰 경로는 **all_products/test_items 180개** 데이터에 고정된 레거시 API다. 이름에 test-items가 있다는 이유로 최신 test_items2 상품 목록/리뷰 API로 사용하지 않는다.

## 4. 접속 문서

| 용도 | 발견한 주소/문서 |
|---|---|
| 서버 내부 | `http://127.0.0.1:8002` — 이번에 healthz 확인 |
| 팀 공유 HTTPS | `https://rag.chanuk.theworkpc.com` — [API 연동 가이드](archive/quality/docs/api/rag-api-guide-2026-10-19.md) |
| Tailscale HTTPS | `https://chancelab-spark.tailbc019f.ts.net:8002` — [DB/API 인수인계서](archive/quality/docs/handover/rag-db-operations-2026-10-19/rag-db-operations-handover-2026-10-19.md) |
| NPM/LAN 전달 | [설정 적용 기록](archive/quality/docs/rag-npm-lan-2026-10-19.md) |

외부 두 주소의 현재 연결 상태는 이번 정리에서 재검사하지 않았다. 5432는 DB 포트, 8002는 HTTP API 포트다. `/`에 웹 화면을 제공하는 API가 아니므로 상태 확인은 `/healthz`를 사용한다.

## 5. 사용자가 요청한 추천 동작과 현재의 차이

조건은 대화에서 확인하는 흐름으로 본다. 과거 `rag-required-intake` 문서는 강제 사전 입력 폼을 만들던 설계 기록이며, 사용자가 그 폼 제거를 요청한 뒤의 현재 화면 요구사항으로 재사용하지 않는다. 원문 목록에 보존한 것은 재도입 승인을 뜻하지 않는다.

| 원하는 동작 | 확인된 구현/자료 | 남은 확인 |
|---|---|---|
| 상품 종류·예산을 먼저 파악 | Brain이 구조화할 계약. RAG는 가격/재고·유형을 받아 검사 | 실제 대화에서 정보가 충분한지 판단하고 구체적으로 재질문하는 E2E |
| 가격 조건을 먼저 충족 | Commerce의 같은 옵션 가격·재고로 검색 전 후보 제한 | 배송비 포함 총액, 실제 판매가 최신성, 화면 가격 일치 |
| 용도에 가장 비슷한 리뷰를 찾기 | BM25/의미 검색, 명시적 후기 요청의 리뷰 전용 채널, 리뷰 근거 우선 선택 | 용도별 사람 라벨, 반대/부정 근거, 최종 설명 충실성 |
| 미달 상품 제외 | 상품 유형·카테고리·옵션 가격·재고 검사 | 임의의 필수 스펙·효능은 현재 모두 자동 검증하지 못함 |
| 특별 옵션은 반드시 지키기 | 구조화된 옵션 정보와 검증된 조건을 사용할 수 있는 계약 | 해당 옵션을 같은 variant에서 검증하는 범용 규칙, 미확인 시 추천 보류 |
| 조회 실패하면 상품 카드 숨기기 | API가 상태/오류/사유를 반환 | Brain·UI가 실패 응답/캐시/부분 도구 결과에서 카드 생성하지 않는지 확인 |
| 여러 카테고리로 확장 | 프로필·유형 레지스트리·카테고리 범위 지원 | 신규 데이터의 원본→색인→모델 준비→프로필 전환 파이프라인 |

“필수 조건 정보가 없으면 패스”는 두 의미를 구분해야 한다. **사용자가 필수 조건을 말하지 않았으면 그 필터를 적용하지 않는다. 사용자가 반드시 요구한 조건인데 상품 정보가 없으면 충족으로 판정하지 않는다.** 현재 API의 미검증 조건 전달과 최종 추천 보류는 소비 측에서도 연결해야 한다.

## 6. 팀 프롬프트와 요청서

- [Agent 기본 지침 v0.6 원문](archive/user-attachments/agent-guidance-v0.6.txt): 팀 리뷰/실제 모델 평가 전 Mock 실험 초안.
- [쇼핑 AI 유저 스토리 원문](archive/user-attachments/shopping-agent-user-stories.txt).
- [시스템 프롬프트 공유 PDF](archive/project/docs/rag-system-prompt-share-2026-10-19.pdf).
- [수정요청서 v1.3](archive/quality/docs/reports/rag-change-requests-2026-10-19-v1.3.md): RR-01~17, 상품명 우선순위, 파우치/파우더 혼동, 운영 경로·데이터·평가·인수인계 요청 포함.

v1.0~v1.3 Markdown/JSON/PDF를 모두 보존했다. 이는 요구사항과 확인 기록이며 항목 전체의 구현 완료나 통과 결과가 아니다. v0.6의 Mock 입력 `status/products/error`와 현재 RAG의 `status/items/error_code` 등 차이도 소비 코드에서 맞춰야 한다. 문서를 모았다는 이유로 이 프롬프트가 현재 LLM 실행 환경에 그대로 적용됐다고 주장하지 않는다.

## 7. 후속 작업 우선순위

1. 현재 Brain/웹이 실제로 호출하는 서버·프로필·코드 버전 추적.
2. 최신 배포 경로의 LangChain HTTP 연결 누락과 브랜치 간 기능 차이를 검토해 통합.
3. 같은 variant 기준의 가격·재고·필수 옵션·최종 카드 정책 일치.
4. 상품명/유형 및 용도 리뷰의 사람 검수 평가셋과 독립 holdout 준비.
5. 전체 카테고리에서 MiniLM/E5/BGE 및 거절 정책을 동일 조건으로 평가.
6. 신규 데이터 적재·재색인·모델 전환·복구 절차를 영구 운영 코드로 정리.

이번 작업의 산출물은 문서와 현황 증거다. 위 후속 작업의 코드 수정·배포·재색인까지 수행한 기록은 아니다.
