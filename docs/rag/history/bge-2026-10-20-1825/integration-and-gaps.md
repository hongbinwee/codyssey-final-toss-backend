# BGE API·Agent 연동과 남은 과제

[목차](README.md) · [현재 BGE 구성](current-system.md) · 확인: 2026-10-20 18:25 KST

## 1. 연결과 역할

| 이름 | 역할 |
|---|---|
| search_rag | AI 추천용 RAG 검색 도구. 실제 서버·데이터·계약을 어댑터에서 맞춰야 함 |
| search_products / searchProducts | Commerce의 일반 상품 목록·카탈로그 탐색. 이름만으로 임베딩 검색을 보장하지 않음 |
| POST /v1/rag/search | 현재 BGE Python 검색 API |
| Brain / 최종 LLM | 예산·용도·상품 종류 확인, 미검증 조건 처리, 설명/카드 생성 |

현재 Python API는 **BM25 + BGE-M3 dense 검색**을 제공한다. 도구 이름이 search_rag여도 Brain이 local RAG나 다른 서버로 연결하면 이 BGE 실행본을 사용하는 것이 아니다. 브라우저부터의 E2E는 이번 자료 갱신에서 재실행하지 않았다.

## 2. 현재 계약은 API 0.2.0

이전 추천 품질 API의 0.3.0 문서와 최신 BGE 실행본을 구분해야 한다. 현재 모델 설정과 OpenAPI를 직접 읽었으며, 실제 요청 스키마도 [JSON으로 저장](current-bge-request.schema.json)했다.

| 요청 항목 | 현재 지원 |
|---|---|
| original_question, query | 필수 문자열 |
| request_id | 선택 추적 ID |
| category | 선택. 생략하면 현재 run의 전체 범주 |
| filters.price_min, price_max, currency | 형식 검증 지원. **가격 하드 필터 적용은 아님** |
| required_conditions, preferences | 배열. 현재는 미검증 조건으로 반환 |
| top_k | 기본 10, 1~20 |
| profile | 현재 요청 스키마에 없음 |
| product_type | 현재 요청 스키마에 없음 |
| filters.in_stock | 현재 요청 스키마에 없음 |

추가 필드 금지 설정이므로 미지원 항목을 포함한 0.3.0 요청은 validation상 422 대상이다. 이 사실은 실행 스키마와 코드에서 확인했으며, 이번 문서 작업 중 오류 POST를 새로 보낸 테스트 결과는 아니다.

### 사용 예시

아래 예시는 현재 지원 형식이며 실제 검색 성공이나 모든 조건 충족을 입증하는 결과가 아니다.

```http
POST /v1/rag/search
Content-Type: application/json
```

```json
{
  "request_id": "bge-doc-example-001",
  "original_question": "통학용으로 5만원 이하 백팩을 찾아줘. 후기도 궁금해",
  "query": "통학용 백팩 후기",
  "category": "fashion",
  "filters": {"price_max": 50000, "currency": "KRW"},
  "required_conditions": [],
  "preferences": ["통학용"],
  "top_k": 5
}
```

**위 price_max는 현재 BGE 엔진에서 적용되지 않고 미검증으로 돌아온다.** 소비 측이 이를 예산을 충족한 추천으로 표시해서는 안 된다.

## 3. 응답 처리

| 항목 | 의미·처리 |
|---|---|
| HTTP 상태, status, error_code | 오류·미준비·결과 없음 구분 |
| dataset_version, supported_categories | 실제 데이터 범위 확인 |
| applied_filters | 현재 category 같은 적용 조건 확인 |
| unverified_conditions | 가격·필수·선호 중 검증하지 못한 요구 |
| items/evidence | 상품 ID·원문 청크·리뷰 ID·출처·offset |
| rrf_score | 채널 순위 결합 점수. 확률/조건 충족률 아님 |

이전 0.3.0의 profile_name, search_context, items.commerce, items.ranking 필드가 현재 BGE 응답에 있다고 가정하지 않는다. 현재 OpenAPI 경로는 `/healthz`와 `/v1/rag/search`이며, 이전 `/v1/catalog/test-items` 목록·리뷰 경로도 현재 이미지에 자동 유지된 것으로 보지 않는다.

DB에는 test_items2/all_products 프로필 정보가 남아 있지만 현재 서비스의 active_run은 최신 active 실행을 고른다. 요청에서 profile=all_products를 보내 기존 색인으로 바꾸는 계약이 아니다.

## 4. 모델 전환과 함께 달라진 기능 범위

| 기능 | 이전 추천 품질 브랜치 | 현재 BGE 실행본 |
|---|---|---|
| 임베딩 | MiniLM 384 | **BGE 1,024**, 전체 준비 |
| 요청 계약 | 0.3.0 확장 | **0.2.0** |
| 프로필 요청 선택 | 지원 | 미지원, 최신 active 선택 |
| 상품 유형/동의어 게이트 | 구현 | 현재 소스에 미통합 |
| 같은 옵션 가격·재고 검증 | CommerceStore 구현 | 현재 경로에 미통합 |
| 후보 확장 | 최대 50개 서로 다른 상품 목표 | 채널별 20청크 |
| 정렬 | 상품명/정체성 어휘 → RRF | RRF → 안정 ID |
| 리뷰 선별 | REAL 우선·중복/짧은 근거 제외 | 해당 개선 미통합 |
| LangChain HTTP invoke | 별도 연결 브랜치에 구현 | 직접 hybrid_search 호출 |

BGE 모델 전환만으로 이전 브랜치의 모든 기능이 합쳐진 것은 아니다. 자료에는 모델 적용 완료와 추천 정책 통합 과제를 따로 표시했다.

## 5. 원하는 추천 동작과 통합 과제

1. 대화에서 상품 종류·예산·용도를 확인한다. 사용자가 제거 요청한 강제 사전 입력 폼을 과거 intake 설계 문서만 보고 재도입하지 않는다.
2. 같은 옵션의 단가·재고·필수 스펙으로 적격 후보를 먼저 정한다. 배송비 포함 총액은 별도 계산한다.
3. 적격 후보의 리뷰를 BM25/BGE로 회수하고 용도와 가까운 원문 근거를 연결한다.
4. 필수 옵션 불일치나 미확인 시 조건 충족 추천으로 표시하지 않는다. 사용자가 조건을 제시하지 않았으면 그 필터를 적용하지 않는 경우와 구분한다.
5. 조회 실패·부분 도구 실패·미검증 필수 조건이 있으면 Brain/UI가 추천 카드를 보류하도록 연동한다.
6. 상품명/상품군·OOD·예산·옵션·리뷰 provenance와 최종 화면 순위까지 평가한다.

현재 BGE API는 3번의 검색 기반을 제공한다. 나머지 모든 검증을 완료한 통합 추천 시스템으로 설명하지 않는다.

## 6. 접속과 운영 자료

- 서버 내부: `http://127.0.0.1:8002`, 이번 healthz 확인.
- 기존 공유 도메인/터널: 과거 API·운영 문서에 보존. 이번에 외부 접속을 재확인하지 않았다.
- [최신 BGE 운영 기록](../../archive/bge-m3-activated/docs/rag-bge-m3-test-items2-full-operations.md).
- [전체 벡터·전환·복구 smoke 보고서](../../archive/bge-m3-activated/reports/rag-bge-m3-test-items2-full-2026-10-20-index.json).
- [이전 0.3.0 API 가이드](../../archive/quality/docs/api/rag-api-guide-2026-10-19.md)는 과거 계약의 참고 자료다.

복구 컨테이너와 예전 MiniLM 벡터는 기존 운영 보고서에 보존 기록이 있다. 이번 작업은 복구/재전환을 실행하지 않았다.

## 7. 프롬프트·팀 요구사항 원문

- [Agent 기본 지침 v0.6](../../archive/user-attachments/agent-guidance-v0.6.txt): Mock 단독 실험 초안.
- [유저 스토리](../../archive/user-attachments/shopping-agent-user-stories.txt).
- [프롬프트 공유 PDF](../../archive/project/docs/rag-system-prompt-share-2026-10-19.pdf).
- [수정요청서 v1.3](../../archive/quality/docs/reports/rag-change-requests-2026-10-19-v1.3.md): 상품명 우선, 유형 혼동, 실제 경로, 가격/옵션, 평가 요구.

문서 수록이 실제 LLM 프롬프트 적용·유저 스토리 구현 완료를 뜻하지 않는다. Mock의 products/error, 현재 RAG의 items/error_code 등 입력 형식도 맞춰야 한다.

## 8. 다음 작업 우선순위

1. Brain 어댑터가 현재 BGE API 0.2.0에 맞게 호출하는지 확인.
2. BGE에 추천 품질 브랜치의 가격/재고·유형·후보/근거 정책과 명시적 프로필을 통합.
3. LangChain Retriever 요청/응답 보존 경로를 통합할지 역할을 명확히 정리.
4. 사람이 검수한 전 카테고리 질의/정답/거절 조건으로 BGE 전체를 평가.
5. v3 재청킹·장문 청크 실험·리랭커는 각각 효과를 분리해 측정.

이 목록은 후속 작업이며 이번 문서 갱신에서 코드·배포·DB를 수정한 기록이 아니다.
