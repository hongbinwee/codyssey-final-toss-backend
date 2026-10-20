# Product RAG — BGE-M3 자료

현재 실행 상태를 기준으로 RAG 관련 문서·데이터 구조·모델 비교·평가·API를 정리한 브랜치입니다.

- **[BGE-M3 전체 자료 목차](docs/rag/README.md)**
- [현재 구성과 메서드 흐름](docs/rag/current-system.md)
- [전체 보고서 PDF](artifacts/rag-bge-m3-full-documentation-2026-10-20.pdf)
- [현재 요청 JSON Schema](docs/rag/evidence/current-bge-request.schema.json)
- [현재 실행 BGE 소스 출처](docs/rag/reference-code/bge-api-compat/source-metadata.json)
- [팀 Git 협업 기준](docs/team-git-workflow.md)

2026-10-20 20:49 KST 확인: 5432/toss_rag, test_items2 전체 114,106개 BGE-M3 1,024차원 벡터 ready. API 0.3.1 복구본을 8002에 적용하고 가격·재고/네 범주 검색을 확인했습니다.

이 문서 브랜치의 기존 src는 24a1051 기반 코드입니다. 현재 실행 BGE 소스는 docs/rag/reference-code/bge-api-compat에 읽기용 사본으로 보관했습니다. 문서 갱신이 애플리케이션 코드를 교체한 것은 아닙니다.

BGE 전환 때 발생한 API 0.2.0 호환성 퇴행을 복구했습니다. [복구·검증 보고서](docs/rag/bge-api-compat-recovery-2026-10-20.md)를 참고하세요. 기존 PDF/ZIP과 원문 아카이브는 작성 당시 기록입니다.

복구 확인 당시의 기록과 현재 공유 상태는 구분합니다. 이후 커밋·푸시 상태는 이 브랜치의 Git 이력과 원격 브랜치를 확인합니다. main에는 병합하지 않았습니다.
