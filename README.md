# Product RAG recommendation quality

기존 5432 PostgreSQL과 상품·리뷰 임베딩을 재사용하는 RAG 서비스입니다.

- [구현 내용·Brain 연동 계약·제약](docs/rag-recommendation-quality.md)
- [요청 JSON Schema](contracts/product-rag/v0.3/request.schema.json)
- [실행 설정 예시](deploy/product-rag-runtime.env.example)
- [팀 Git 협업 기준](docs/team-git-workflow.md)
- [작업 정리 PDF · 5쪽](docs/reports/rag-recommendation-quality-summary-2026-10-19.pdf)

현재 브랜치의 코드는 구현 및 공유를 위한 상태이며, 실행 중인 API나 기존 색인을 교체하지 않았습니다.
PDF와 구현 기록의 상태 표시는 커밋·푸시 전 작성 시점의 스냅샷입니다.
이후 공유 상태는 Git 커밋과 원격 브랜치를 기준으로 확인합니다.
