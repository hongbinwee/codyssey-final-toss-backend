# BGE-M3 dense 검색 전환 및 비교 설계

작성일: 2026-10-20
상태: 사용자 검토용 설계

## 목표

`test_items2/beauty`에서 기존 MiniLM 인덱스와 청크를 보존하면서 BGE-M3 dense 벡터를 추가한다. 같은 데이터와 질의로 다음 구성을 비교한다.

1. BM25 단독
2. BM25 + BGE-M3 dense
3. BGE-M3 dense 단독

평가가 끝나기 전에는 현재 서비스의 활성 데이터나 검색 설정을 바꾸지 않는다.

## 현재 상태와 근거

- 현재 실행 경로는 FastEmbed의 `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`를 사용한다. 임베딩 차원은 384이고, DB 열도 `vector(384)`다.
- 현재 청크 버전은 `source-evidence-token-v2:max_tokens=96`이다.
- `test_items2/beauty` 비교 보고서에는 상품 781개, 리뷰 34,545개, 청크 78,595개, 긍정 질의 10개와 범위 밖 질의 2개가 기록돼 있다.
- 기존 보고서의 BGE-M3 8/10 Hit@1은 BM25 Top 20과 BGE-M3 dense Top 20을 RRF로 결합한 결과다. BGE-M3 dense 단독은 측정하지 않았다.
- 기존 기대 상품 라벨은 규칙 기반 임시 라벨이라 수치는 탐색적 결과다. 사람 검수 없이 확정 정확도로 표현하지 않는다.
- FastEmbed의 현재 지원 목록에 BGE-M3는 없다. BGE-M3 공식 구현인 FlagEmbedding은 CPU 실행을 제공하며, BGE-M3 dense 출력은 1,024차원이다.

## 선택한 구성

### 임베딩 실행

- 기존 MiniLM 실행기는 FastEmbed로 유지한다.
- BGE-M3에는 별도 임베딩 어댑터를 추가하고 FlagEmbedding의 `BGEM3FlagModel`에서 dense 출력을 사용한다.
- 문서와 질문을 BGE-M3의 corpus/query 인코딩 경로로 각각 임베딩한다. BGE-M3 검색에는 별도 query 지시문을 붙이지 않는다.
- 초기 비교에서는 BGE-M3 sparse와 ColBERT 출력을 사용하지 않는다. 키워드 채널은 기존 BM25로 고정한다.
- CPU 실행을 기본으로 지원하고, 초기화 시간·질의 지연·메모리 사용량을 기록한다. GPU 설정은 이 작업의 필수 조건으로 두지 않는다.

### 저장 구조와 검색

- 기존 `rag.evidence_chunks.embedding vector(384)`를 변경하거나 덮어쓰지 않는다.
- `rag.index_run_embedding_profiles`에 모델별 프로필을 추가한다. 프로필은 `run_id`, `embedding_model`, 모델 revision, 차원, 최대 입력 길이, 상태와 청크 수를 기록하며, `(run_id, embedding_model)`로 식별한다.
- `rag.evidence_chunk_embeddings`에는 `run_id`, `chunk_id`, `embedding_model`, `vector(1024)`를 저장한다. 기존 청크 행과 프로필을 모두 외래 키로 참조하고, `(run_id, chunk_id, embedding_model)`가 기본 키다.
- 기존 `index_runs.embedding_model`은 최초 색인 모델 기록으로 유지한다. 추가 임베딩 모델의 사용 가능 여부는 새 프로필 테이블에서 판단한다.
- BGE-M3 벡터는 1,024차원으로 저장하고, 색인 완료 시 모든 대상 청크의 벡터가 존재하는지 확인한다.
- BM25는 기존 ParadeDB 검색을 계속 사용한다. Hybrid 검색은 현재 RRF 설정을 유지한다. Dense 단독 모드는 BM25 채널을 호출하지 않고 BGE-M3 vector rank만으로 상품 순위를 만든다.
- 기존 384차원 MiniLM 벡터와 활성 서비스 인덱스는 비교 및 롤백을 위해 보존한다.

## 청킹과 재색인

- 첫 모델 비교에서는 청크 본문과 경계를 다시 만들지 않는다. DB에 저장된 `embedding_text`를 그대로 BGE-M3에 넣어 모델 차이만 비교한다.
- 이 단계는 재청킹이 아니라 기존 청크 전체의 BGE-M3 재임베딩이다. 대상은 `test_items2/beauty`의 기존 78,595개 청크다.
- 과거 BGE-M3 비교와 입력 조건을 맞추기 위해 첫 재임베딩 최대 길이는 128토큰으로 둔다. 기존 청크는 96토큰 상한이므로 원문 청크 경계는 그대로 유지한다.
- 청크 크기 조정은 별도 후속 실험으로 분리한다. 96토큰 외의 후보 크기가 필요하다고 판단되면, 같은 평가 질의로 청크 길이별 인덱스를 만들고 새 청크를 모두 재임베딩한다.

## 평가 방식

- 비교 대상은 같은 `test_items2/beauty` 데이터 스냅샷과 같은 검색 질의다.
- 먼저 기존 질의 10개와 범위 밖 질의 2개를 사용해 과거 보고서와 직접 비교한다.
- `Hit@1`, `Hit@5`, `Macro Recall@5`, `Macro MRR@5`, `Macro Precision@5`, 범위 밖 질의 반환 수와 질의별 결과를 기록한다.
- BM25 단독은 기존 결과를 기준선으로 포함한다. 두 BGE 구성은 동일한 BGE 벡터 집합을 사용해 검색 채널만 달리한다.
- 라벨이 기존 규칙 기반 상태라면 새 결과도 탐색적 평가로 표시한다. 모델 우열을 확정하기 전에는 관련성 라벨의 사람 검수를 별도 진행한다.

## 데이터베이스 및 활성화 범위

- DB 작업은 팀 지침에 따라 `5432/toss_rag`에서만 수행한다. `15436`에는 연결하지 않는다.
- 변경은 기존 데이터 보존형 DDL과 신규 BGE 벡터 행 추가로 제한한다. 기존 MiniLM 벡터나 활성 인덱스는 삭제하지 않는다.
- `test_items2/beauty` 비교가 끝나도 운영 검색 설정을 자동 전환하지 않는다. 활성화는 결과 검토와 사용자 지시 후 별도 단계로 한다.

## 고려한 대안

| 대안 | 검토 결과 |
| --- | --- |
| FastEmbed에서 모델명만 BGE-M3로 변경 | 현재 공식 지원 목록에 모델이 없어 선택하지 않는다. |
| 기존 384차원 벡터 열을 1,024차원으로 바로 교체 | MiniLM 기준을 잃고 되돌리기 어려워 선택하지 않는다. |
| BGE-M3 전환과 동시에 청크 크기도 확대 | 모델과 청킹 효과가 섞여 BM25 제거 비교를 해석하기 어려워 첫 비교에서는 제외한다. |
| 기존 청크 보존 후 별도 BGE 임베딩 저장 | 비교 조건과 롤백 경로를 유지하므로 선택한다. |

## 주요 위험과 확인 항목

- BGE-M3는 569M 파라미터, 약 2.27GB 모델이다. CPU에서 인덱싱 시간이 길 수 있으므로 실행 시간과 메모리를 측정한다.
- 78,595개 청크의 1,024차원 float32 벡터만 계산해도 원시 벡터가 약 0.30 GiB를 차지하며, DB 행과 인덱스 비용은 별도다.
- BGE-M3 문서의 최대 입력 길이 8,192토큰이 긴 청크가 검색에 더 좋다는 뜻은 아니다. 먼저 현재 96토큰 청크로 모델 비교를 끝낸다.
- 기존 10개 긍정 질의만으로는 일반적인 검색 정확도를 확정할 수 없다. 결과 보고서에 표본 수와 라벨 한계를 함께 표기한다.

## 참고

- [test_items2 full-corpus activation record](../../../reports/rag-bge-m3-test-items2-full-2026-10-20-index.json)
- [FastEmbed 지원 모델 목록](https://qdrant.github.io/fastembed/examples/Supported_Models/)
- [BGE-M3 모델 카드](https://huggingface.co/BAAI/bge-m3)
- [FlagEmbedding 단일 장치 CPU 예제](https://github.com/FlagOpen/FlagEmbedding/blob/master/examples/inference/embedder/encoder_only/m3_single_device.py)
