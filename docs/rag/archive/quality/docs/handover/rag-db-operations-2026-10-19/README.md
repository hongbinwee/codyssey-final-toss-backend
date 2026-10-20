# 운영 인수인계 자료

먼저 rag-db-operations-handover-2026-10-19.md 또는 공유 PDF를 읽으세요.

- 기본 API: https://chancelab-spark.tailbc019f.ts.net:8002
- PostgreSQL: 같은 호스트 5432, 원본 DB toss / 색인 DB toss_rag
- Postman: rag-api-tailscale.postman_collection.json Import
- 원본: toss → test_items2 → products/product_variants/reviews
- 청크/벡터: toss_rag → rag → evidence_chunks, 활성 profile=test_items2
- sql/ 파일은 명시된 DB에서 읽기 전용으로 실행합니다.
- *.schema.sql은 DDL 참고/복원용이며 운영 DB에 자동 실행하지 않습니다.
- 모델 변경 장에는 현재의 384차원 제약과 아직 없는 재색인 CLI를 명시했습니다.
- 모델 교체/재색인/검색 품질 테스트는 이 문서 작성에서 실행하지 않았습니다.
- 비밀번호·인증키·실제 runtime.env·previous-container.json·모델 가중치·대용량 데이터 ZIP은 이 자료에 포함하지 않습니다.
