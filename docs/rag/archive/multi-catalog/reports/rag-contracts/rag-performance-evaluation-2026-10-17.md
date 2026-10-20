# RAG retrieval evaluation — 2026-10-17

- Endpoint: `http://127.0.0.1:8002/v1/rag/search`
- Data source: `5432/toss_rag` / profile `all_products`
- Active dataset: `test_items:sha256=4e9924492dcb536e:products=180:reviews=4737`
- Indexed products: 180 (category support reported by health: beauty)
- Retrieval: top_k=5; category left unset to match all-catalog search.
- Labels: provisional source-title proxies; no human relevance judgments were supplied.

## Metrics

- Positive queries with a title-based target: 10/10
- Hit@1: 60.0%; Hit@5: 80.0%
- Macro Recall@5: 48.3%; MRR@5: 0.700; Precision@5 (returned items): 34.0%
- Negative unsupported queries returning products: 2/2
- HTTP 200: 12/12; status=ok: 12/12
- Latency: median 68 ms; p95 nearest-rank 81 ms; max 81 ms.
- Returned product IDs present in active DB run: 42/42; evidence snippets/IDs/offsets exact-match active chunk rows: 118/118.

## Query results

| Query | Expected title proxy count | Hit@1 | Relevant ranks (Top 5) | Top 3 returned | Status | ms |
|---|---:|:---:|---|---|---|---:|
| 잡티를 가려줄 컨실러 추천 | 2 | ✓ | 1,4 | [24시간커버지속/올리브영 6년연속 1등] 루나 롱래스팅 팁 컨실러 EX 20colors<br>[레오파드 헬로키티]웨이크메이크 쉐이킹 블러 치크&쉐딩<br>[NEW산리오캐릭터즈] 롬앤 베러 댄 컨투어 (쿠로미) | ok | 68 |
| 블러셔 추천 | 4 | ✗ | — | [남성 선물 추천] 우르오스 2종 세트 택1(지복합성, 중건성)<br>[세은 PICK/트러블1등] 셀라딕스 트러블 세범 리밸런싱 131 앰플 30ml<br>[레오파드 헬로키티]웨이크메이크 쉐이킹 블러 치크&쉐딩 | ok | 64 |
| 아이라이너 추천 | 5 | ✓ | 1,2 | [NO.1 아이라이너] 클리오 샤프 쏘 심플 워터프루프 펜슬라이너 단품/더블기획<br>[한정수량1+1] 키스미 스무스 리퀴드 아이라이너 N (3 color) (단품/기획)<br>페리페라 맑게 물든 선샤인 치크 (젤리/파우더 2타입) | ok | 71 |
| 눈썹용 브로우 추천 | 3 | ✓ | 1,4 | 페리페라 스피디 스키니 브로우 8 Colors<br>셀리맥스 더 비타 A 레티날 샷 타이트닝 듀얼 크림 50ml<br>[1등 모공 수분천재크림] 에스네이처 아쿠아 스쿠알란 수분크림 60ml 기획 (+크림 30ml) | ok | 65 |
| 입술 보습 립밤 추천 | 5 | ✗ | — | [파데프리/더마비비] 에스쁘아 더마커버 블레미쉬 밤 40g 3colors SPF 50 PA++++ 비비크림<br>[1등품절템/웜쿨대통합] 프레시안 에그라이크 크림 블러쉬 (단독 기획)<br>[화잘먹/볼륨광미스트] 디어달리아 엔드리스 스킨 크림 미스트 | ok | 81 |
| 건조할 때 바르는 수분 크림 추천 | 13 | ✗ | 2,3,4 | 에스트라 아토베리어365 크림미스트 120ml<br>[8월올영픽/속수분크림] 웰라쥬 리얼 히알루로닉 수딩 크림 80ml 기획(+20ml)<br>[1등 모공 수분천재크림] 에스네이처 아쿠아 스쿠알란 수분크림 60ml 기획 (+크림 30ml) | ok | 67 |
| 트러블 피부에 쓰는 토너 추천 | 6 | ✓ | 1,4 | [트러블 피부 추천/저자극 각질 케어] 제로이드 핌프로브 토너 200ml<br>[트러블 피부 추천/붉은기 진정 앰플] 제로이드 핌프로브 카밍 앰플 30ml 기획 (+크림 10ml)<br>[1등 모공 수분천재크림] 에스네이처 아쿠아 스쿠알란 수분크림 60ml 기획 (+크림 30ml) | ok | 76 |
| SPF 50 비비크림 추천 | 1 | ✗ | 2 | [트러블 피부 추천/저자극 각질 케어] 제로이드 핌프로브 토너 200ml<br>[파데프리/더마비비] 에스쁘아 더마커버 블레미쉬 밤 40g 3colors SPF 50 PA++++ 비비크림<br>[UPGRADE] 이니스프리 레티놀 시카 모공 흔적 크림 50ml 기획(+30ml) | ok | 67 |
| 우르오스 올인원 스킨밀크 200ml | 1 | ✓ | 1 | 우르오스 올인원 스킨밀크 200ml<br>[베스트 올인원]우르오스 올인원 200ml 2종 택 1<br>[NEW/단독기획] 토리든 다이브인 저분자 히알루론산 수딩 크림 100ml (+20ml) | ok | 76 |
| 민감하고 건조한 피부에 장벽 보습 크림 | 20 | ✓ | 1,2,3,5 | 에스트라 아토베리어365 크림미스트 120ml<br>[8월올영픽/NO.1 국민수분크림] 키엘 울트라 훼이셜 크림 28ml/50ml/150ml (기획/단품)<br>에스트라 아토베리어365 하이드로 수딩크림 80ml 기획 (+수딩크림 10ml+클렌징폼 30g) | ok | 66 |
| 클렌징 오일 추천 | 0 (unsupported) | — | — | [1등 보송젤파우더] 오브제 오일 컨트롤 피니셔 5g 단품<br>[레오파드 헬로키티]웨이크메이크 쉐이킹 블러 치크&쉐딩<br>[9/13 단하루특가] 유니딧 브로우 무드 스위치 베이지 브라운 60g | ok | 75 |
| 게임용 기계식 키보드 적축 추천 | 0 (unsupported) | — | — | [남성 선물 추천] 우르오스 2종 세트 택1(지복합성, 중건성)<br>[7일특가/13호, 19호 출시] 힌스 메쉬 매트 쿠션 6 Colors 한정 기획 (+리필+글리터밤)<br>[트러블 피부 추천/저자극 각질 케어] 제로이드 핌프로브 토너 200ml | ok | 64 |

## Interpretation

The title-proxy metrics estimate whether retrieval returned products whose source titles match the requested product type. They do not certify subjective recommendation quality, feature truth, price correctness, or all-category coverage. Unsupported-query results are a separate false-positive check.
