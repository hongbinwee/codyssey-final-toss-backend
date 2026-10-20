# Nginx Proxy Manager → RAG LAN 연결 적용

기준일: 2026-10-19 (Asia/Seoul).

## 원인과 조치

사용자가 NPM 목적지를 http://172.30.1.53:8002로 수정했으나, RAG API 프로세스는 127.0.0.1:8002에만 바인딩되어 LAN 접속이 거부됐다. 변경 전 도메인 /healthz는 502였다.

시스템 socket unit toss-rag-lan.socket에 172.30.1.53:8002 수신을 추가했다. toss-rag-lan.service는 기본 제공 systemd-socket-proxyd로 127.0.0.1:8002에 전달한다. 기존 API의 loopback 바인딩과 Tailscale Serve의 같은 포트 바인딩을 유지한다. 새 포트·DB·색인은 만들지 않았다.

원본 unit 파일: deploy/systemd/toss-rag-lan.socket, toss-rag-lan.service.
설치 위치: /etc/systemd/system/. socket unit은 enable --now로 활성화했다. 부팅 시 socket을 만들고 요청 시 서비스를 시작한다. LAN 주소 172.30.1.53이 바뀌면 unit과 NPM 주소를 함께 갱신해야 한다.

## 현재 NPM 설정

- Domain: rag.chanuk.theworkpc.com
- Scheme: http
- Forward Hostname/IP: 172.30.1.53
- Forward Port: 8002
- 외부 주소: https://rag.chanuk.theworkpc.com
- NPM 설정은 사용자가 수정했다. 이 작업에서는 NPM 관리자 설정을 변경하지 않았다.

## 확인 범위

- http://127.0.0.1:8002/healthz → 200, test_items2.
- http://172.30.1.53:8002/healthz → 200, test_items2.
- https://rag.chanuk.theworkpc.com/healthz → 200, test_items2.
- http 도메인의 /healthz → https로 이동 후 200.
- 기존 Tailscale HTTPS 경로 /healthz → 200, test_items2.
- 도메인 루트 / → 404 {"detail":"Not Found"}. RAG API는 루트 웹 화면을 제공하지 않으므로 /healthz 또는 POST /v1/rag/search를 사용한다.
- unit 설정 검사와 활성 상태를 확인했다. 검색 POST·추천 품질 테스트는 실행하지 않았다.

## 되돌리기

sudo systemctl disable --now toss-rag-lan.socket
sudo systemctl stop toss-rag-lan.service

이렇게 하면 LAN 수신만 중단된다. 기존 127.0.0.1 API 및 DB·색인은 유지된다.

## 저장/반영 상태

서버의 LAN 연결 설정은 적용했다. 위 unit 파일과 이 문서는 Backend feature/rag-recommendation-quality 작업 트리에 로컬 저장했다. 이번 변경의 Git 커밋·푸시·main 병합은 수행하지 않았다.
