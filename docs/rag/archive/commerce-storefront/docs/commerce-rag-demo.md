# Commerce RAG 데모

이 checkout은 `hongbinwee/codyssey_final-mission-main`의 고정 commit 위에 구성한 프론트엔드 작업본입니다. 검색과 근거는 기존 `test_earphones` RAG 색인(API `127.0.0.1:8002`)에서 읽습니다. 상품 ID를 정확히 연결하기 위해 Commerce 데모 DB에도 같은 합성 이어폰 fixture를 적재하고, 가격·재고·variant와 상세/장바구니는 Commerce DB 기준으로 읽고 씁니다.

## 실행

기존 RAG API `127.0.0.1:8002`가 실행 중이고 `/healthz`에 `test_earphones`와 `earphones`가 있는지 확인합니다. 새 Commerce DB와 system identifier 준비는 RAG 저장소의 [격리 데모 runbook](../../commerce-rag-integration/docs/commerce-rag-demo.md)을 따릅니다. Commerce용 env의 `RAG_API_BASE_URL`은 `http://127.0.0.1:8002`로 설정합니다. 이 runner는 DB identity와 RAG dataset marker를 확인한 뒤에만 시작합니다.

새 Commerce DB에 스키마와 기본 데모 데이터를 넣고 이어폰 fixture를 추가합니다.

```bash
npm run db:migrate -- --phase=6
npm run db:seed -- --phase=4
npm run db:seed:demo
npm run db:seed:earphones-test
```

이어폰 seed는 `commerce` DB 안의 `earphone-test-*` ID 범위에만 upsert하며 RAG 색인 DB에는 쓰지 않습니다.

Commerce 저장소에서 브라우저 실행에 필요한 로컬 설정을 로드합니다.

```bash
set -a
. /path/to/rag-repository/.commerce-rag-demo.local/compose.env
. /path/to/rag-repository/.commerce-rag-demo.local/identity.env
set +a
```

그 다음 아래 명령은 RAG mode 전용 config/spec만 실행합니다.

```bash
npm run test:rag-demo
```

테스트는 접근 코드로 세션을 만들고, 이어폰 통화 품질·배터리를 검색해 `earphone-test-002`의 상품 설명/합성 리뷰 근거를 확인합니다. 이어서 상세에서 variant를 선택하고 장바구니의 상품 ID와 가격까지 검사합니다. checkout과 결제는 실행하지 않습니다.

브라우저에서 직접 둘러보려면 위 환경 변수를 로드한 Commerce 저장소에서 전용 runner를 실행합니다.

```bash
node tests/rag-demo/server.ts
```

`http://127.0.0.1:13001`을 열고 접근 코드 `demo`로 로그인합니다. runner를 종료하면 화면 서버만 멈추며, 데모 DB와 색인은 그대로 유지됩니다.

일반 `npm run verify`, `test:e2e`, integration 또는 legacy Playwright 경로는 이 데모 테스트에 포함되지 않습니다. 종료할 때는 RAG runbook의 Compose project 서비스만 `stop`하고, 생성된 데이터 볼륨은 보존합니다.
