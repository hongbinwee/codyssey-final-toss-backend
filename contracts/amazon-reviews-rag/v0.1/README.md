# Amazon Reviews RAG v0.1 공동 계약

이 디렉터리는 사용자에게 승인받은 BM25 + FastEmbed + LangChain 하이브리드 검색 기준을 구체화합니다. DB/API 담당자와 Agent 담당자의 최종 계약 검토는 별도입니다.

| 파일 | 용도 |
|---|---|
| `source.schema.json` | API 상품·리뷰를 연결한 RAG 내부 정규화 입력. 기존 API의 page envelope를 대체하지 않습니다. |
| `request.schema.json` | Agent→RAG 검색 요청. original_question과 query가 필수입니다. |
| `response.schema.json` | RAG→Agent 검색 결과. 상품 ID, 원본 출처, 필드·오프셋·문자열을 포함합니다. |
| `examples/source.json` | 현재 API에 존재하는 Lascar 상품과 Linux 관련 리뷰. |
| `examples/request.json` | 해당 리뷰를 찾는 한국어 요청. |
| `examples/response-ok.json` | 완성된 성공 응답 형식. 상품·리뷰와 근거는 실제 원본이며 순위·RRF 점수는 설명용 가정입니다. 실제 검색 결과가 아닙니다. |
| `examples/response-no-results.json` | 후보가 없는 응답. |
| `examples/response-low-relevance.json` | 후보는 있지만 관련성 기준에 미달하여 items를 비운 응답. |
| `examples/response-error.json` | 활성 색인이 없는 오류 응답. |

## 필드 규칙

- 상품 연결 키는 `(category, parent_asin)`이고 결과의 product_id에는 parent_asin을 사용합니다. dataset_version은 스냅샷을 식별합니다.
- 리뷰 source_id는 API가 생성한 review_key입니다. 상품 source_id는 parent_asin입니다.
- source_field는 `title`, `text`, `features[0]`, `description[1]`, `details["Brand"]`처럼 원본 필드를 가리킵니다. JSON 객체 키는 JSON 인용 문자열로 표시합니다.
- start_offset은 포함, end_offset은 제외이며 Python 문자열과 같은 Unicode 코드 포인트 인덱스입니다. 원본 문자열을 정규화하거나 HTML 태그를 제거한 뒤 오프셋을 매기지 않습니다.
- 숫자·불리언 등 비문자 상세 값은 원본 값의 canonical JSON 표현(UTF-8, sort_keys, 공백 없는 구분자)을 근거 문자열로 사용합니다. null·빈 값은 청크로 만들지 않습니다.
- user_id는 원본 정규화 단계에서 중첩 필드까지 제거합니다. 상품 영상 메타데이터 안에도 user_id가 있으므로 최상위 키 제거만으로는 충분하지 않습니다.
- 원본 payload의 선택 필드는 그대로 보존합니다. 누락된 필드는 추정하지 않습니다. 가격에 통화가 없으면 통화 조건은 적용하지 않고 unverified_conditions에 표시합니다.
- top_k는 상품 후보 수이며 기본 10, 범위 1–20입니다. 상품당 근거는 1–3개입니다.
- BM25와 벡터는 동일한 embedding_text를 각각 검색합니다. 채널별 초기 후보 20개, RRF k=60, 동일 가중치를 사용합니다. rrf_score는 확률이 아닙니다.
- RRF에 필요한 순위, 상품·출처 버전 연결, 오프셋 길이 같은 교차 필드 제약은 `scripts/rag_contracts.py`에서도 검사합니다. JSON Schema만으로 검사되지 않는 제약이 있습니다.

## 상태와 오류

| 상태 | items | error_code |
|---|---|---|
| ok | 최소 1개 | null |
| no_results | 빈 배열 | null |
| low_relevance | 빈 배열 | null |
| error | 빈 배열 | 안정된 오류 코드 |

ok/no_results/low_relevance에는 dataset_version이 필수입니다. error에서는 활성 색인 확인 전 실패한 경우 null을 허용합니다. 허용 오류 코드는 invalid_request, index_not_ready, embedding_failed, database_failed, configuration_error, search_failed, timeout입니다. HTTP 검증 실패는 422와 error/invalid_request를 함께 사용합니다.

low_relevance의 판정 임계값은 tuning 질문과 음성 사례에 대한 팀 판정으로 교정합니다. 임의 수치를 검증된 기준으로 간주하지 않습니다.
