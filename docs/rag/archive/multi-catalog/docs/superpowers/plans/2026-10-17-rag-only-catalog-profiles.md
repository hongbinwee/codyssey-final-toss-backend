# 5432 RAG 인덱스 프로필 연결 계획

**Goal:** `5432/toss_rag`에 이미 적재된 `test_items` 청크를 기본 검색 대상에서 반환하고, 이어폰 인덱스는 별도 프로필로 보존한다. 쇼핑 화면도 RAG DB의 상품 payload와 evidence만으로 검색 추천을 표시한다.

**Architecture:** `rag.index_profiles`가 프로필별 활성 run을 지정하고 `rag.index_runs.profile_name`이 run 소속을 기록한다. 기존 run과 chunk를 보존하면서 test_items run은 `all_products`, 이어폰 run은 `test_earphones`로 귀속한다. 8002 API 기본값을 `all_products`로 설정한다. 화면은 `/v1/rag/search`가 돌려준 `product_metadata`를 직접 사용하며 별도 상품 DB를 조회하지 않는다.

**Tech Stack:** Python, FastAPI, PostgreSQL/pgvector, SQL migration, TypeScript storefront.

**Spec:** `docs/superpowers/specs/2026-10-17-rag-catalog-profiles-design.md` (사용자 수정 지시 우선 적용)

**Global Constraints:** 사용자의 지시에 따라 RAG 데이터베이스 `5432/toss_rag`만 사용한다. 다른 DB에 연결하거나 조회하지 않는다. 기존 run/chunk/임베딩을 삭제하거나 재생성하지 않는다. `main`에 병합하거나 원격 push하지 않는다. 카테고리는 코드에 열거하지 않고 DB의 활성 run에서 동적으로 읽는다. 상품 추천은 RAG에 저장된 정보만 표시하고 존재하지 않는 상세 옵션·가격·재고 정보를 만들어내지 않는다.

**Review Focus:** 프로필 간 활성 run 격리, 마이그레이션의 재실행 안전성, 8002의 실제 profile/dataset health, 검색 응답의 정확한 RAG 상품 payload, category 하드코딩 및 다른 DB 의존성 제거.

## Task 1: 프로필별 활성 run 저장 구조

**Files:**
- Create: `deploy/migrations/20261017_rag_index_profiles.sql`
- Update: `deploy/product-rag.sql`
- Update: `src/toss_ads/rag/store.py`
- Update: `tests/test_rag_store.py`

1. `active_run(profile_name)`과 프로필별 `activate_dataset`의 기대 동작을 테스트로 먼저 작성하고, 현재 전역 활성 run을 사용해 테스트가 실패하는지 확인한다.
2. migration으로 `profile_name`과 `rag.index_profiles`를 추가하고 단일 전역 active 제약을 프로필별 제약으로 바꾼다. test_items run은 `all_products`, 이어폰 run은 `test_earphones`로 연결한다.
3. store가 profile별 run을 읽고 같은 profile만 supersede하도록 최소 변경한다. activation 포인터는 같은 트랜잭션에서 갱신한다.
4. 테스트를 다시 실행해 통과시키고 migration 재실행/기존 run·chunk 보존을 확인한다.

## Task 2: API 기본 프로필 및 색인 실행 안전장치

**Files:**
- Update: `src/toss_ads/rag/config.py`
- Update: `src/toss_ads/rag/api.py`
- Update: `src/toss_ads/rag/retriever.py`
- Update: `src/toss_ads/rag/indexer.py`
- Update: `src/toss_ads/rag/__main__.py`
- Update: corresponding API/indexer/config tests

1. `RAG_DEFAULT_PROFILE` 기본값과 `/healthz` profile 필드를 검증하는 테스트를 먼저 추가한다.
2. 검색기가 설정된 프로필 run만 선택하게 한다. 없는 프로필은 not-ready로 응답하고 이어폰 등 다른 프로필로 fallback하지 않는다.
3. `--profile`을 색인 CLI에 추가한다. 카테고리 일부만 처리한 run이 `all_products` 포인터를 덮어쓰지 못하도록 막고, test run은 별도 프로필에서 활성화한다.
4. 변경 후 관련 테스트를 실행해 통과시키고 기존 색인 보호 로직을 확인한다.

## Task 3: 화면에서 RAG 상품 payload 직접 표시

**Files:**
- Update carefully, preserving existing edits: storefront `src/contracts.ts`
- Update carefully, preserving existing edits: storefront `src/rag-search.ts`
- Update carefully, preserving existing edits: storefront `src/rag-demo-safety.ts`
- Update carefully, preserving existing edits: storefront `src/web/screens/Search.tsx`
- Update carefully, preserving existing edits: corresponding `tests/unit/rag-search.test.ts`, `tests/unit/rag-search-ui.test.ts`, `tests/unit/rag-demo-safety.test.ts`

1. 테스트를 먼저 작성해 category 미지정 검색 요청이 이어폰 category를 추가하지 않고, RAG 응답의 product metadata를 그대로 반환하는지 확인한다.
2. 제한된 `digital|earphones` 타입, `test_earphones` 데이터 버전 추출, 이어폰 고정 UI 배지를 제거한다. category가 지정되지 않으면 RAG 전체 profile 검색으로 보낸다.
3. storefront의 `hydrate`/별도 카탈로그 DB 조회에 의존하지 않고 RAG 응답의 `product_id`, category, title, brand, image, price payload 및 evidence로 추천 카드를 렌더한다. 가격/재고의 simulated 여부를 유지하며 없는 정보는 표시하지 않는다.
4. 서비스 preflight는 8002 health의 `all_products` profile과 실제 dataset 상태를 확인하도록 바꾼다. RAG 오류 시 일반 상품 검색 결과로 대체하지 않는다.
5. 관련 테스트와 타입 검사를 실행한다. 기존 미커밋 변경은 보존하고 `main`에는 반영하지 않는다.

## Task 4: 5432 migration 및 8002 서비스 반영

**Files:**
- Apply: `deploy/migrations/20261017_rag_index_profiles.sql` to `5432/toss_rag`
- Rebuild/restart: `toss-rag-api-beauty` on port 8002 with `RAG_DEFAULT_PROFILE=all_products`

1. 적용 직전 `5432/toss_rag`에서 두 run의 ID, 상태, 제품·리뷰·chunk 수를 읽고 기록한다.
2. additive migration만 적용한다. 기존 임베딩과 청크 수가 그대로인지, 각 profile 포인터가 지정한 run을 가리키는지 확인한다.
3. 해당 RAG API 코드로 8002 서비스를 갱신하고 기본 profile을 설정한다. 다른 데이터베이스는 사용하지 않는다.
4. `/healthz`가 `all_products`와 test_items dataset/categories를 반환하는지 확인한다.

## Task 5: 실제 검색 회귀 평가

**Files:**
- Create: `tests/evals/catalog_profile_smoke.jsonl`

1. 앞서 직접 검색한 여섯 beauty 질의를 재현 가능한 eval 입력으로 기록한다.
2. 실행 중인 8002에 같은 질의를 보내 응답 상품 ID가 test_items run 소속이고 category 필터 없이 전체 profile에서 검색되는지 확인한다.
3. `test_earphones` run을 별도 경로로 확인해 기존 이어폰 profile 결과가 보존됐는지 검증한다.
4. RAG DB 밖에서 상품 조회를 하지 않는지 화면 검색 요청과 payload 흐름을 검증하고 결과를 요약한다.

## Plan Self-Review

- 사용자의 마지막 지시에 따라 검색·UI 모두 `5432/toss_rag`만 사용하며 다른 DB는 계획에서 제외했다.
- 기존 청크/임베딩 보존과 main 미병합을 명시했다.
- 실제 RAG payload에 없는 product detail/variant/cart 정보를 생성하지 않는다.
- 실제 8002 런타임 반영과 동일 질의 검색 검증까지 완료 조건에 포함했다.
