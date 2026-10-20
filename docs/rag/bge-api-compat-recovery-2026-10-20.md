# BGE API 호환성 복구 — 2026-10-20

## 원인과 적용 상태

BGE 전환 때 임베딩 모델뿐 아니라 API 구현도 이전 0.2.0 기반으로 배포됐다.
기존 0.3.0의 `profile`, `product_type`, `filters.in_stock` 요청은 422로 거부됐고,
Commerce 가격·재고 검증과 기존 catalog 경로도 빠졌다. 8002 포트와 healthz 자체는 접속 가능했다.

**20:48 KST에 API 0.3.1 호환 복구본을 기존 8002에 적용했다. BGE는 유지했다.**

| 항목 | 적용 결과 |
|---|---|
| 이미지 | `toss-ads-product-rag-service:bge-api-compat-20261020` |
| 모델 | BAAI/bge-m3, 1,024차원, revision `5617a9f61b028005a4858fdac845db406aefb181` |
| 검색 데이터 | `test_items2`, 상품 1,500개 / 리뷰 46,100개 / BGE 벡터 114,106개 |
| 검색 DB | **5432/toss_rag**, rag 스키마 |
| 원본 옵션 검증 DB | **5432/toss**, test_items2 스키마 |
| 기본 프로필 | **test_items2** — 새 active run이 생겨도 다른 프로필로 자동 변경하지 않음 |
| 가격·재고 | 같은 variant 행에서 예산·재고 확인 후 그 상품 ID만 BM25/BGE에 전달 |
| API | `POST /v1/rag/search`, 기존 확장 요청·응답 메타데이터 복원 |
| healthz | 모델명·차원·프로필·Commerce 구성 여부 표시 |
| 복구 컨테이너 | `product-rag-api-before-compat-20261020-114819`, 정지 상태로 보존 |

원본·청크·벡터·프로필 포인터를 수정하거나 재임베딩하지 않았다.

## 검증

- 별도 8003 후보에서 10개 HTTP 검사 통과 후 8002 교체.
- 8002에서도 동일한 10개 검사 통과: health, 기존 실패 요청, 네 범주, 0원 예산 제외,
  기존 최소 요청, legacy catalog/reviews, API 버전/경로.
- 과거 422 요청이 200/ok, 예산 이내 상품 3개로 응답.
- 로컬 이외 LAN 및 두 HTTPS 주소의 health/search 모두 200.
- 반환된 **옵션 15건의 가격·재고**, **근거 43건의 상품·출처 관계**를 읽기 전용 SQL로 대조.
- BGE 준비 수량 114,106/114,106, revision·차원·범위 재확인.
- 회귀 테스트 **9/9** 통과. LangChain BGE 생성 오류도 실패 재현 후 수정.
- 별도 코드 검토에서 critical/important 없음; minor 1건을 회귀 테스트와 함께 수정.

실제 응답·검사 결과: [검증 JSON](evidence/rag-bge-api-compat-verification-2026-10-20.json).
검색 요청의 관찰 시간은 약 0.3~1.9초였으며 부하·정확도 평가 결과는 아니다.

## 호출 예시

```http
POST /v1/rag/search
Content-Type: application/json
```

```json
{
  "request_id": "bge-compatible-001",
  "original_question": "통학용 백팩을 찾아줘",
  "query": "백팩",
  "profile": "test_items2",
  "category": "fashion",
  "product_type": "backpack",
  "filters": {"price_max": 50000, "currency": "KRW", "in_stock": true},
  "top_k": 3
}
```

서버 내부는 `http://127.0.0.1:8002`, LAN은 `http://172.30.1.53:8002`.
공유 주소는 [RAG API 문서](https://rag.chanuk.theworkpc.com/docs).
Tailscale `chancelab-spark.tailbc019f.ts.net:8002`는 **HTTPS**를 사용한다.
검색은 POST이며 GET 요청이나 `/` 화면으로 검색 성공을 판단하지 않는다.

## 호환성과 남은 범위

- 0.2 클라이언트가 응답의 추가 필드를 금지한다면 `profile_name`, `search_context`,
  `commerce`, `ranking` 등 복원된 0.3 필드를 수용해야 한다. 원격 웹의 실제 파서를 확인한 것은 아니다.
- 웹/Brain/최종 LLM까지의 E2E는 미확인이다. 로컬 storefront 프로세스가 실행 중이지 않았다.
- 임의의 `required_conditions`/`preferences`는 여전히 미검증 목록이다. 자동 스펙 필터를 구현한 것으로 설명하지 않는다.
- `/v1/catalog/test-items`와 리뷰 경로는 **기존 test_items 180개 전용**이다. 검색 기본 데이터 1,500개와 구분한다.
- `all_products`에 BGE 준비 프로필이 없으면 검색은 안전하게 `index_not_ready`로 거부한다.
- BGE는 FlagEmbedding 직접 호출이다. LangChain `HybridRagRetriever`는 BGE 객체를 받을 수 있지만,
  HTTP 경로는 여전히 `hybrid_search`를 직접 실행한다.

## 저장·공유 상태

코드는 Backend **feature/rag-bge-api-compat** worktree에 로컬 저장했고 실행 컨테이너에 적용했다.
20:49 복구 확인 당시에는 커밋·GitHub 푸시 전이었다. 이후 공유 상태는 각 브랜치의 Git 이력과 원격 브랜치를 따른다. main에는 병합하지 않았다.
이전 BGE 컨테이너와 기존 MiniLM 복구 컨테이너를 보존했다.
