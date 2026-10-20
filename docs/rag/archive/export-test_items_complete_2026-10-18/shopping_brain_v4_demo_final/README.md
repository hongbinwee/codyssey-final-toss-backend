# Shopping Brain v4 — 실제 상품 통계 기반 시연용 데이터셋 (검증 범위 명시)

**데이터셋 생성 완료(수량): 상품 180개 / 모의 Variant 180개 / 합성 리뷰 4737건.**

**공식 검증 완료된 상용 최종본은 아님:** 제조사 제품군 수준 검증은 4개, 176개는 원본 목록+리뷰 집계 기반의 **시연용 정보 안내** 수준이다. 전성분·효능·정확한 선택 옵션을 추측하거나 생성하지 않았으며, 이 단계의 설명은 제조사 인증 제품 사양으로 사용할 수 없다.

- 상품명/브랜드/과거 혜택가/대표 이미지 URL/상품별 실제 관측 후기 분포: 실제 GitHub 올리브영 상품 및 리뷰 데이터를 Codex가 분석한 보강 파일을 기반으로 함.
- **원본 후기 텍스트는 이 패키지에 존재하지 않음.** 리뷰 4737건은 통계 분포 및 제품 유형을 기반으로 시뮬레이션한 `SYNTHETIC` 의견이며 실구매자의 후기가 아니다.
- 과거 상품가격을 기반으로 만든 **단일 대표 Variant와 재고는 모의 쇼핑 옵션**이다. 이는 실물 SKU·진짜 재고·옵션별 실제 가격이 아니다. `spec_overrides`에 표시.
- 500자 이상 텍스트는 5섹션. 제조사 근거 4개 외 나머지는 출처 한계·비교 가이드 중심으로 작성됨. 제품 기능 상세 설명이 정식으로 검증됐다는 뜻이 아님.
- 이미지 URL: 외부 이미지 참조. 이미지 파일을 다운로드/재배포하지 않았으며 화면 표시 가능/사용 권한은 별도 확인 필요.
- **자동 DB 적재 금지.** 독립 테스트용 Commerce DB에서만 수동 검토 후 사용. 기존 v3·main·DB 수정 없음.

## 파일
- `db/seeds/v4_demo_catalog.json`: Commerce Seed 형태 `{products,variants}`; 가격·재고 모의
- `db/seeds/v4_demo_reviews.json`: `source_kind=SYNTHETIC` 합성 리뷰
- `rag/product_sections_v4.jsonl`: 5개 섹션 × 180개. 출처 검증등급 포함
- `rag/review_documents_v4_demo.jsonl`: 가상 리뷰용 RAG 문서
- `rag/variant_documents_v4_demo.jsonl`: 모의 옵션 RAG 문서
- `evidence/product_provenance_v4.jsonl`: 공식 검증 여부·원본 관측·표시 상태 구분
- `evidence/source_product_facts_v4.jsonl`: Codex 원본 사실 정규화, 분석 출처
- `evidence/observed_review_aspect_aggregate_v4.jsonl`: 실제 후기의 규칙기반 집계 **원문 아님**
- `evidence/verified_manufacturer_facts_v4.jsonl`: 공식 출처가 확인된 4개 제품군
- `qa/PRODUCT_QA.csv`, `qa/QA_SUMMARY.json`, `qa/OBSERVED_VS_SYNTHETIC_RATINGS.json`: 검수
- `docs/DATA_CONTRACT.md`, `docs/RELEASE_GATES.md`: 적재·검수 정책

## 리스크
평점 원본은 인기 상품 수집 기반으로 5점 비중이 높아 전체 쇼핑몰 대표성이 없다. 원본 정형 스펙이 없어 제품별 효능·성분·사용 방법은 176개 상품에서 미확인 상태다. 합성 리뷰에 나타나는 체감은 테스트를 위한 가상 의견이지 소비자 근거가 아니다.

- `scripts/rebuild_v4_from_evidence.py`: 패키지 안에 포함된 근거 파일만으로 재생성하는 결정론적 스크립트. `python3 scripts/rebuild_v4_from_evidence.py`
- `preview/`: 상품·가상 리뷰 미리보기.
