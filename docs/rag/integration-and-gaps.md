# BGE API·Agent 연동과 남은 범위

[목차](README.md) · [현재 구성](current-system.md) · **2026-10-20 20:49 KST**

## 1. 연결과 역할

| 이름 | 역할 |
|---|---|
| search_rag | AI 추천용 RAG 도구. 실제 API 주소·요청·응답 계약을 맞추는 어댑터 필요 |
| search_products / searchProducts | Commerce 일반 카탈로그 탐색. 이름만으로 임베딩 검색을 보장하지 않음 |
| POST /v1/rag/search | BM25+BGE 및 가격·재고 검증을 제공하는 Python API |
| Brain / 최종 LLM | 대화·예산/용도 확인, 미검증 조건 처리, 설명·상품 카드 |

도구 이름과 실제 연결 주소를 함께 확인해야 한다. 원격 웹부터의 E2E는 아직 검증하지 않았다.

## 2. 현재 계약은 API 0.3.1

BGE 전환 때 배포된 0.2.0이 기존 요청을 422로 거부한 문제를 복구했다. [실제 검증](evidence/rag-bge-api-compat-verification-2026-10-20.json) · [실행 요청 스키마](evidence/current-bge-request.schema.json).

| 요청 항목 | 지원/처리 |
|---|---|
| original_question, query | 필수 문자열 |
| request_id | 선택 추적 ID |
| profile | 선택, 기본 **test_items2**. 해당 프로필의 active 포인터 선택 |
| category | 선택, 생략하면 선택 run의 전체 범주 |
| product_type | 선택, 유형 레지스트리와 정체성 게이트 적용 |
| filters.price_min, price_max, currency | KRW 같은 variant 가격으로 검색 전 검증 |
| filters.in_stock | 재고 조건. 기본 런타임은 true |
| required_conditions, preferences | 임의 조건은 미검증 목록으로 반환 |
| top_k | 기본 10, 허용 1~20 |

```json
{
  "request_id": "bge-compat-example-001",
  "original_question": "통학용 백팩을 찾아줘",
  "query": "백팩",
  "profile": "test_items2",
  "category": "fashion",
  "product_type": "backpack",
  "filters": {"price_max": 50000, "currency": "KRW", "in_stock": true},
  "top_k": 3
}
```

동등한 요청을 실제 API에 보내 200/ok와 예산 내 상품 3개를 확인했다. 임의 필수 스펙이나 배송비까지 검증한 예시는 아니다.

## 3. 응답·오류 처리

| 항목 | 처리 |
|---|---|
| HTTP/status/error_code | 오류·미준비·결과 없음·관련성 부족 구분 |
| profile_name/dataset_version | 실제 선택 데이터 확인 |
| applied_filters | 검증하여 적용한 가격·재고·유형·범주 |
| items.commerce | 선택 옵션 ID·가격·재고·검증 시점·모의값/출처 상태 |
| items.product_metadata.price | 선택된 Commerce 옵션 가격 반영 |
| items.evidence | 청크·상품·리뷰 ID·원문·offset·출처 |
| items.ranking/search_context | 랭킹·관련성·후보 처리 정보 |
| unverified_conditions | 검증하지 못한 필수 조건·선호 |
| rrf_score | 순위 결합 점수, 충족 확률이 아님 |

0.2 응답 필드만 허용하는 strict parser는 복원된 0.3 필드를 받아야 한다. **실제 원격 client가 이 parser를 사용한다는 증거는 없다.** 서버 검색 성공과 웹 표시 성공을 구분한다. 오류·미확인 필수 조건에서 카드를 보류하는 정책은 Brain/UI까지 확인해야 한다.

## 4. catalog·프로필 구분

- 기본 BGE 검색은 **test_items2 1,500상품**이다.
- 복원한 `/v1/catalog/test-items`와 `/{product_id}/reviews`는 **test_items 180상품**에 고정된 기존 호환 경로다. 새 전체 catalog API라고 안내하지 않는다.
- `all_products` 요청은 별도 프로필을 선택한다. 해당 BGE 프로필이 준비되지 않았다면 `index_not_ready`로 거부하며 MiniLM로 몰래 전환하지 않는다.
- 이번 복구에서 프로필 포인터·데이터·청크·벡터를 변경하지 않았다.

## 5. 접속·검증

- 서버 내부 `http://127.0.0.1:8002`, LAN `http://172.30.1.53:8002`.
- [공유 API 문서](https://rag.chanuk.theworkpc.com/docs).
- Tailscale `https://chancelab-spark.tailbc019f.ts.net:8002`는 HTTPS 사용.
- healthz와 POST 검색을 LAN/두 HTTPS 경로에서 확인했다. `/`는 UI가 아니고 검색은 GET이 아니다.
- [복구 내역·롤백·검증](bge-api-compat-recovery-2026-10-20.md).

## 6. 다음 확인할 작업

1. 실제 웹의 search_rag가 복구된 API를 호출하고 0.3 응답을 파싱하는지, 최종 카드까지 확인.
2. 대화의 예산·용도·특수 옵션과 서버 필터/미검증 조건을 일관되게 연결. 강제 사전 입력 폼 재도입은 사용자 요구가 아니다.
3. 필수 옵션 불일치·미확인, 배송비 총액, 도구 부분 실패에서 카드 보류 검증.
4. 사람이 검수한 전 범주 질의/정답/거절 조건으로 BGE 추천 정확도 평가.
5. LangChain HTTP invoke 연결의 역할을 확정하고, v3 재청킹·리랭커 효과는 별도 비교.

## 7. 팀 요구사항 원문

[Agent 기본 지침 v0.6](archive/user-attachments/agent-guidance-v0.6.txt), [유저 스토리](archive/user-attachments/shopping-agent-user-stories.txt), [프롬프트 공유 PDF](archive/project/docs/rag-system-prompt-share-2026-10-19.pdf), [수정요청서 v1.3](archive/quality/docs/reports/rag-change-requests-2026-10-19-v1.3.md).

수록 자체가 프롬프트 적용·모든 유저 스토리 구현을 뜻하지 않는다. 이전 [18:25 기록](history/bge-2026-10-20-1825/README.md)은 복구 전 상태다.
