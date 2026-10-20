# Toss Ads AI Project

토스 `AI Engineer (Ads)` 포지션을 목표로 설계한 광고 도메인 AI 시스템 포트폴리오 프로젝트입니다.

현재는 합성 데이터와 공개적으로 설명 가능한 규칙을 바탕으로 광고주 경험과 플랫폼 운영 문제를 재현하는 오프라인 MVP를 개발합니다. 실제 토스 내부 데이터·정책·광고 집행은 사용하지 않습니다.

## 프로젝트 방향

1. 자연어 목표와 예산을 구조화된 캠페인으로 변환
2. 광고 소재와 설정을 정책 관점에서 검토하고 근거와 함께 결과 제공
3. 성과 이상을 찾아 원인과 다음 조치 제안
4. 상품 정보와 캠페인 목표에 맞춰 소재 요구사항과 초안 구성

현재 구현은 캠페인 요청에서 `CreativeSpec`을 만들고 형식별 제약을 검증하는 평가 가능한 세로 슬라이스입니다.

## 문서

- [프로젝트 설계](docs/superpowers/specs/2026-09-26-toss-ads-ai-engineer-design.md)
- [CreativeSpec 계약](docs/creative-spec.md)
- [평가 데이터 안내](evals/README.md)
- [뷰티 상품 검색 품질 점검](docs/rag-search-quality-test-items-beauty-2026-10-17.md) ([원시 평가 결과](reports/rag-search-quality-test-items-beauty-2026-10-17.json))

## 원칙

- 평가 가능한 작은 세로 슬라이스부터 구현합니다.
- 구조화된 출력, 검증, 근거를 우선합니다.
- 실제 사용자·광고주 데이터와 비공개 정책은 저장하지 않습니다.
- 모델 품질과 비즈니스 지표, 운영 안정성을 함께 측정합니다.
- 특정 LLM 제공자에 종속되지 않는 어댑터 경계를 유지합니다.

## 실행

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
PYTHONPATH=src python3 scripts/run_eval.py
```

RAG 검색 품질 보고서에는 현재 `test_items/beauty` 색인에 직접 보낸 검색 요청과 수동 점검 결과가 기록되어 있습니다. 검색 API는 `127.0.0.1:8002`에서 실행 중입니다.
