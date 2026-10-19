# Backend 작업 지침

작업 시작 전 [팀 공통 Git 협업 기준](docs/team-git-workflow.md)을 읽는다.
이 문서가 Git 협업 규칙의 정본이며 오래된 메모의 미확정 표기보다 우선한다.

- RAG 개발 대상은 `hongbinwee/codyssey-final-toss-backend` 저장소다.
  변경·커밋·푸시 전에 Git 루트와 remote가 이 저장소인지 확인한다.
- 새 RAG 브랜치는 `feature/rag-<작업명>`으로 만든다.
  `codex/`나 `feature/gaon-`을 RAG 팀 명명 규칙으로 적용하지 않는다.
- 최신 Commerce와 공통 개발 기준을 공유하는 main에서 역할별 브랜치로 개발한다.
  실제 main의 통합 상태는 별도로 확인하고 완료를 추정하지 않는다.
- 기능 반영은 PR → 검토 → 사용자 지시에 따른 main 병합 순서다.
  main 직접 커밋·직접 푸시·지시 없는 병합은 하지 않는다.
- 새 worktree에서도 이 지침과 정본 문서를 읽을 수 있게 연결한다.
- RAG 실행·검증 DB는 `5432/toss_rag`를 사용한다. `15436`에 연결하거나 조회하지 않는다.
- 로컬 파일, 커밋, GitHub 푸시, main 반영 상태를 구분해서 보고한다.
