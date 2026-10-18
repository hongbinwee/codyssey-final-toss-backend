# 팀 공통 Git 협업 기준 — 정본

기준일: 2026-10-18
출처: 사용자가 공유한 협업 구조와 RAG 브랜치 명명 규칙 정정.

## 공통 개발 흐름

최신 Commerce 코드와 공통 개발 기준을 main에 통합한 뒤, 팀원들은 그 공통 기준에서
브랜치를 만들어 독립적으로 개발한다.

| 브랜치 예시 | 역할 |
| --- | --- |
| main | 최신 Commerce + 공통 개발 기준 |
| feature/rag | RAG · 검색 알고리즘 |
| feature/agent | LangGraph · Agent |
| feature/data | Amazon 데이터 마이그레이션 |
| feature/prompt | 시스템 프롬프트 |

완료된 기능부터 Pull Request → 검토 → main 병합 순서로 공통 코드에 반영한다.

## RAG 작업 기준

- 개별 RAG 작업 브랜치는 `feature/rag-<작업명>` 형식으로 만든다.
- 예: `feature/rag-langchain-http`.
- `codex/` 또는 `feature/gaon-`을 팀 규칙으로 추정해 사용하지 않는다.
- RAG 개발 대상은 `hongbinwee/codyssey-final-toss-backend` Backend 저장소다.
- 작업·커밋·푸시 전 Git 루트와 remote를 확인하고 상위 프로젝트와 혼동하지 않는다.

## main 반영

- 이 문서는 협업 기준이다. 현재 main의 Commerce 통합 완료를 확인한 기록이나
  지금 main 통합을 실행하라는 지시는 아니다.
- main 직접 커밋·직접 푸시는 하지 않는다.
- 실제 main 병합은 PR 검토와 사용자 지시를 거친다.

## 참조와 갱신

- 원래 프로젝트와 Backend 저장소의 AGENTS.md가 이 문서를 참조한다.
- 새 worktree의 AGENTS.md에서도 이 정본을 읽도록 연결한다.
- 오래된 메모와 충돌하면 이 문서와 최신 사용자 지시를 기준으로 정정한다.
- 대화에서 규칙이 바뀌면 이 문서와 참조 지침을 함께 갱신한다.
- 로컬 저장, 커밋, GitHub 푸시, main 반영 상태를 구분해서 보고한다.

로컬 저장이 GitHub 공유나 main 반영을 뜻하지는 않는다.
