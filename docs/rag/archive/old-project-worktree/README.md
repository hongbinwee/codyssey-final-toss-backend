# Toss Final Project

토스 `AI Engineer (Ads)` 포지션을 목표로 설계한 광고 도메인 AI 시스템 포트폴리오 프로젝트입니다.

현재 단계는 합성 데이터와 공개적으로 설명 가능한 규칙을 기반으로 광고주 경험과 플랫폼 운영 문제를 재현하는 오프라인 MVP입니다. 실제 토스 내부 데이터·정책·광고 집행은 사용하지 않습니다.

## 프로젝트 방향

하나의 광고 운영 흐름을 다음 네 가지 AI 기능으로 연결합니다.

1. 자연어 목표와 예산을 구조화된 캠페인으로 바꾸는 캠페인 설정 도우미
2. 광고 소재와 설정을 정책 관점에서 검토하고 근거 있는 결과를 만드는 광고 심사 자동화
3. 성과 이상을 찾고 원인과 다음 조치를 제안하는 성과 보고 인사이트
4. 상품 정보와 캠페인 목표를 바탕으로 이미지·포스터·영상 소재 요구사항과 초안을 구성하는 소재 생성 워크플로

현재 구현 단위는 캠페인 요청에서 `CreativeSpec`을 만들고 형식별 제약을 검증하는 평가 가능한 세로 슬라이스입니다. 이후 심사, 보고, 실제 멀티모달 생성기를 같은 스키마와 평가 원칙 위에 추가합니다.

## 문서

- [프로젝트 설계](docs/superpowers/specs/2026-09-26-toss-ads-ai-engineer-design.md)
- [CreativeSpec 계약](docs/creative-spec.md)
- [평가 데이터 안내](evals/README.md)
- [Amazon Reviews'23 데이터와 API 안내](data/amzdata/README.md)
- [Amazon Reviews API 명세](docs/amazon-reviews-api.md)

## 원칙

- 평가 가능한 작은 세로 슬라이스부터 구현합니다.
- LLM의 자유로운 답변보다 구조화된 출력, 검증, 근거를 우선합니다.
- 실제 사용자·광고주 데이터와 비공개 정책은 저장하지 않습니다.
- 모델 품질뿐 아니라 비즈니스 지표와 운영 안정성까지 함께 측정합니다.
- 특정 LLM 제공자에 종속되지 않는 어댑터 경계를 유지합니다.

## DGX Spark에서 실행

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
PYTHONPATH=src python3 scripts/run_eval.py
```

현재 기준선은 결정론적 planner와 validator입니다. 다음 단계에서 자연어 파서, 정책 심사, 성과 인사이트, 이미지·영상 생성 API를 붙이더라도 이 계약과 오프라인 평가를 통과해야 합니다.

## 원격 작업 공간

```bash
ssh -p 10022 aiteam@100.114.218.1
cd /home/aiteam/projects/toss-ads-project
```

## Amazon Reviews'23 상품·리뷰 API

선별 데이터에는 상품 30,000개와 리뷰 178,335개가 있습니다. API는 원본 데이터를 PostgreSQL에서 조회하며, RAG 데이터는 같은 PostgreSQL 데이터베이스의 별도 스키마로 분리할 수 있습니다. 저장 구조와 API 주소는 [데이터 안내](data/amzdata/README.md)와 [API 명세](docs/amazon-reviews-api.md)를 참고하세요.

API는 기존 경로, 요청 매개변수와 응답 형식을 유지합니다. PostgreSQL 포트는 호스트 로컬에만 열려 있고, API 호출은 기존 내부 주소 또는 Nginx Proxy Manager를 거치는 도메인으로 합니다.
