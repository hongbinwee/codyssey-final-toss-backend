# 공통 작업 규칙 참조

Git 협업·브랜치 명명·PR 검토·main 반영 기준은
[팀 공통 Git 협업 기준](team-git-workflow.md)을 읽고 적용한다.

RAG 작업 브랜치는 `feature/rag-<작업명>`이며, 개발 대상은 Backend 저장소다.
RAG 실행·검증 DB는 `5432/toss_rag`를 사용한다.

현재 구현 범위는 [서비스 안내](../deploy/product-rag-runtime/README.md)와
[LangChain 구성도](../deploy/product-rag-runtime/docs/langchain-architecture.md)를 참고한다.
로컬 파일·커밋·GitHub 푸시·main 반영 및 코드 작성·실행 검증 상태를 구분해서 보고한다.
