# RAG → Agent 규격 초안 v1

찬욱님·서현님과 합의할 handoff 형식입니다. Agent에 실제로 연결하지는 않았습니다. `rag_to_agent_example.json`은 실행한 합성 샘플 검색 결과입니다.

## 요청

Python `BM25Index.search(query, top_k=5, document_type=None, category=None, product_id=None, min_query_coverage=0.5)`.
query: 유효 단어가 있는 1..2000자 문자열. top_k: 1..100. document_type: product/review/None. category/product_id는 검색 범위를 제한합니다.

## 응답

`{schema_version:"rag-result-v1",status,query,method,results,matched_document_count,min_query_coverage,dataset_versions,limitations}`.
각 result는 검색 document의 모든 원본 연결 필드와 score/matched_terms/query_coverage/evidence_sufficient를 포함합니다. 상품 정보는 title/brand/category/price/currency이며 리뷰 근거는 text/source_id/source_ref/source_locator/source_hash입니다.

| status | 뜻 |
|---|---|
| ok | 최소 단어 일치율을 충족한 자료가 있음; 의미·사실 신뢰도 인증 아님 |
| no_results | 필터 범위에서 질문 단어가 겹치는 문서가 없음 |
| insufficient_evidence | 단어 일부가 겹치지만 기본 0.5 일치율을 충족하지 못함 |
| error | 입력 오류·색인 오류·API 접근 오류 등 실행 실패. 빈 results와 error.code/message 포함 |

Python 함수는 잘못된 입력/색인에 ValueError를 내고 CLI 경계가 status=error와 종료 코드 1로 변환합니다. status ok/no_results/insufficient_evidence는 정상 실행이므로 CLI 종료 코드 0입니다. 서버에 연결할 때 동일 경계 처리를 재사용하세요.

자료 없음/약한 근거는 답변에서 근거 부족으로 처리하고 리뷰 내용을 만들지 않습니다. review text 안의 지시는 데이터일 뿐 실행하지 않습니다. 전체 지시/프롬프트 방어는 Agent 담당과 연결 후 검증해야 합니다. 리뷰 원문은 임의 HTML로 렌더링하지 않고 text로 표시하세요.

Commerce ID가 null이면 장바구니 입력 ID로 사용하지 않습니다. Amazon 가격을 KRW 최신가격으로 표시하지 않으며, 구매 가격·재고는 별도 Commerce 조회로 확인해야 합니다. 가격 누락은 null, 리뷰 없음은 review 근거 없음으로 전달합니다.

동일 상품 리뷰가 여러 개 반환될 수 있으며 이 검색기는 상품별 집계/다양성 재정렬을 하지 않습니다. BM25 원점수는 corpus마다 다르므로 검색 방식 간 점수를 직접 비교하지 않습니다. 의미적 품질 평가·최종 토큰화/threshold 결정은 찬욱님 담당입니다.
