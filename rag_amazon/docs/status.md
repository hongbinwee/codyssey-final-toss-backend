# 공유용 실행 상태

2026-10-15 KST 기준.

실제 실행: 제공된 Amazon API에서 3개 범주별 10상품씩 받아 상품30/리뷰224를 확보했습니다. category+parent_asin으로 연결하고 review_key·원문·출처·버전을 보존한 문서254개를 만들었습니다. BM25Okapi 색인을 JSON으로 저장/복원하고 원본과 대조했습니다. 최종 client로 실제 API 상품1/리뷰5 재조회도 확인했습니다.

검증: 단위/회귀22개 통과, 실제 고정 검색 smoke6/6 통과. 자료 없음/낮은 단어 일치율/입력 오류를 구분합니다. 독립 코드 검토에서 나온 원본 덮어쓰기·토큰없는문서·스키마검증·URL검증 문제를 수정하고 재검토했습니다. 실제 dataset 전체 검색 품질 평가 결과는 아닙니다.

Mock: examples/mock_snapshot.json과 examples/mock/는 별도 합성 규격/색인 예시입니다. 실제 실행본은 examples/real_api/입니다.

미구현/미해결: Commerce product/variant ID 확정 매핑, Agent 실제 통합, 임베딩·Hybrid, 3만상품 전량 색인, GitHub 반영/PR. 입력 price는 과거 USD로 최신 KRW 구매가격과 구분합니다. API category는 잘못 분류된 원본 사례도 그대로 유지합니다.

찬욱님에게 전달: client/preprocess/text/index 및 CLI, processed_documents/corpus/tokenized_corpus/bm25_index, DB→RAG·RAG→Agent 규격 초안과 실제 샘플 JSON, README. 라이브러리·tokenizer·응답규격을 합의한 다음 실제 검색 평가를 이어가면 됩니다.
