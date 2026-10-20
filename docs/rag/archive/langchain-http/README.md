# Codyssey Final Toss Backend

Initial test commit to verify repository write access.

## LangChain RAG HTTP service

- [서비스 코드와 실행 안내](deploy/product-rag-runtime/README.md)
- [LangChain 구성도](deploy/product-rag-runtime/docs/langchain-architecture.md)
- [연결 검증 기록](reports/langchain-http-verification-2026-10-18.json)
- [팀 Git 협업 기준](docs/team-git-workflow.md)

이 브랜치는 실행 중인 test_items RAG HTTP 서비스와 LangChain Retriever 연결을 담습니다.
Commerce 전체를 main에 통합한 상태를 의미하지 않습니다.

다른 개발 환경에서는 다음과 같이 서비스 이미지를 빌드할 수 있습니다.

```sh
cd deploy/product-rag-runtime
docker build -t product-rag-runtime:local .
```

Dockerfile.runtime은 기존 서버의 의존성 이미지가 있을 때 사용하는 소스 교체용 파일입니다.
