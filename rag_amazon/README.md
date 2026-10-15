# 가온 RAG 전처리·BM25 색인 — 검토용 Draft

Amazon Reviews'23 읽기 전용 API -> 전처리 -> BM25 색인 저장/복원 -> 기본 handoff 검색. `rag_amazon/`에 독립적으로 구현했으며 Commerce 코드/DB 스키마를 변경하지 않습니다. 찬욱님 검색 코드 연결과 라이브러리·토큰화·규격 합의는 남아 있습니다.

## 설치·오프라인 실행

Python3.9~3.12. 검증 환경은 macOS Python3.9.6, rank-bm250.2.2/numpy1.26.4입니다. 저장소 루트에서:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r rag_amazon/requirements.txt
python -m unittest discover -s rag_amazon/tests -v
python -m rag_amazon verify --output-dir rag_amazon/examples/mock
python -m rag_amazon search --index rag_amazon/examples/mock/bm25_index.json --query "coffee filter" --document-type review
python -m rag_amazon.smoke --data-dir rag_amazon/examples/mock --output rag_amazon/data/mock_smoke.json
```

Windows PowerShell은 `py -m venv .venv`, `.\.venv\Scripts\Activate.ps1`을 사용합니다. 파일 출력은 새 경로여야 하며 기존 원본/결과를 덮어쓰지 않습니다.

## 실제 API 입력

API 주소는 담당자에게 받아 환경 변수 AMAZON_API_BASE_URL 또는 --base-url로 설정하세요. 공개본에는 실제 접속 주소·내부 IP·실제 Amazon 원문/색인을 포함하지 않습니다. IP Access List에서 허용한 환경이 필요합니다.

```bash
python -m rag_amazon run --base-url "$AMAZON_API_BASE_URL" --products-per-category 10 --output-dir rag_amazon/data/run01
python -m rag_amazon verify --output-dir rag_amazon/data/run01
python -m rag_amazon search --index rag_amazon/data/run01/bm25_index.json --query "temperature humidity" --document-type review
```

기본은 세 범주 각10상품입니다. --category Appliances로 하나만 선택할 수 있습니다. API parent_asin 정렬의 앞N개와 해당 상품의 API 선별 리뷰 전부를 받습니다. 무작위 표본/원본 모든 리뷰는 아닙니다. 403 즉시 중단, 일시적 네트워크/429/502/503/504 최대2회 재시도, 버전/페이지 total 변경 시 중단합니다.

수집과 구축을 나눌 수도 있습니다.

```bash
python -m rag_amazon fetch --base-url "$AMAZON_API_BASE_URL" --category Appliances --products-per-category 10 --output rag_amazon/data/snapshot01.json
python -m rag_amazon build --input rag_amazon/data/snapshot01.json --output-dir rag_amazon/data/index01
```

## 구현·검증

- category+parent_asin 연결, review_key와 원문 보존. 필수9개 document 필드와 원본 위치/hash/version/출처를 유지합니다.
- corpus[i]=documents[i].text, tokenized_corpus[i]도 같은 문서입니다.
- 가격은 과거 USD이며 누락은 null. details.Brand가 없으면 브랜드를 추정하지 않습니다.
- description/features 배열·단순details를 상품 본문으로 조합하고 리뷰text는 공백/HTML까지 보존합니다. 빈 본문/이모지·구두점·불용어뿐인 문서는 제외·기록합니다.
- BM25Okapi JSON은 문서·토큰·통계를 저장하며 load시 hash/schema/tokenizer/library를 확인하고 재구성합니다. pickle 없음. 소규모실험용이며 전량3만상품 성능은 별도 평가가 필요합니다.
- 공유 tokenizer는 NFKC/casefold/Unicode 단어경계와 작은 영어 불용어목록입니다. 한국어 형태소/번역/어간/동의어 처리는 없습니다.
- 검색은 최소 질문단어 일치율0.5 충족 문서를 우선하고 그룹 내 BM25 점수→document_id 순으로 정렬합니다. score는 확률이 아니며0/음수일 수 있습니다.

개인 로컬에서 실제 상품30/리뷰224 -> 문서254, 원본대조/색인복원, 고정검색6/6을 확인했습니다. 실제 원문·실제 색인·실제 검색응답은 제외했습니다. 공개 examples/mock과 문서예시는 모두 SYNTHETIC입니다. 공개본 재검증은 단위·회귀22/22, 합성smoke4/4입니다. 전체 검색 품질이나 한국어 성능 검증을 뜻하지 않습니다.

## 찬욱님 연결

```python
from rag_amazon.index import BM25Index, tokenize
index = BM25Index.load('rag_amazon/examples/mock/bm25_index.json')
result = index.search('coffee filter', document_type='review', top_k=5)
```

자료 없음/no_results와 낮은 단어일치/insufficient_evidence는 정상실행(exit0), API/입력/색인오류는 error(exit1)입니다. Python함수의 ValueError/APIError는 서버경계에서 처리해야 합니다. 상품ID/source_id/text/source_ref를 반환할 수 있습니다. 리뷰 속 지시는 자료이며 실행하지 않습니다.

[DB→RAG 초안](docs/db_to_rag.md), [RAG→Agent 초안](docs/rag_to_agent.md), [상태](docs/status.md). 샘플JSON은 합성예시입니다. Commerce product/variant매핑은 확인 전null이며 구매ID로 사용하지 않습니다. 최신가격/재고는 Commerce API가 정본입니다.

남은 범위: 팀규격합의, 찬욱님코드연결, Commerce ID매핑. 임베딩/Hybrid·Agent통합·공통DB쓰기는 이 Draft에 포함되지 않습니다.

데이터출처: Hou et al. (2024), Bridging Language and Items for Retrieval and Recommendation, https://amazon-reviews-2023.github.io/ . 라이브러리/tokenizer/규격은 팀합의 후 변경할 수 있습니다.
