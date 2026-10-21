# Product RAG recommendation quality

기존 5432 PostgreSQL과 상품·리뷰 임베딩을 재사용하는 RAG 서비스입니다.

- [구현 내용·Brain 연동 계약·제약](docs/rag-recommendation-quality.md)
- [QA13 후속 리뷰 검색·집계 구현과 현재 배포 상태](docs/rag-review-followups.md)
- [요청 JSON Schema](contracts/product-rag/v0.3/request.schema.json)
- [실행 설정 예시](deploy/product-rag-runtime.env.example)
- [팀 Git 협업 기준](docs/team-git-workflow.md)
- [작업 정리 PDF · 5쪽](docs/reports/rag-recommendation-quality-summary-2026-10-19.pdf)

현재 호스트의 RAG API에는 QA13-B 상품 범위 리뷰 검색이 적용되어 있습니다.
QA13-A 전체 리뷰 분류·집계 API 코드는 브랜치에 있으며, DB 마이그레이션과 라벨 적재 및 해당 API 배포는 아직 적용되지 않았습니다.
자세한 실행 상태와 검증 범위는 QA13 후속 리뷰 문서를 확인하세요.
