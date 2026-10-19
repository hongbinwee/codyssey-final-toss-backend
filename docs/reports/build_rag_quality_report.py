"""Build the Korean implementation handoff PDF from reviewed project records."""
from pathlib import Path
from xml.sax.saxutils import escape
import json

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Flowable, KeepTogether

ROOT = Path('/home/aiteam/projects/toss-ads-project')
HERE = Path(__file__).resolve().parent
OUT = HERE / 'rag-recommendation-quality-summary-2026-10-19.pdf'
FONT = ROOT / 'presentations/assets/fonts'
pdfmetrics.registerFont(TTFont('Pretendard', str(FONT / 'Pretendard-Regular.ttf')))
pdfmetrics.registerFont(TTFont('PretendardMedium', str(FONT / 'Pretendard-Medium.ttf')))
pdfmetrics.registerFontFamily('Pretendard', normal='Pretendard', bold='PretendardMedium')

INK = colors.HexColor('#172B46')
MUTED = colors.HexColor('#5F7187')
BLUE = colors.HexColor('#1764E8')
PALE = colors.HexColor('#F1F6FF')
TEAL = colors.HexColor('#087E80')
BORDER = colors.HexColor('#DCE4EF')
LIGHT = colors.HexColor('#F6F8FB')
AMBER = colors.HexColor('#8E5F0A')
PAGE_W, PAGE_H = A4
WIDTH = PAGE_W - 88
styles = {
    'title': ParagraphStyle('title', fontName='PretendardMedium', fontSize=25, leading=33, textColor=INK, wordWrap='CJK', spaceAfter=9),
    'subtitle': ParagraphStyle('subtitle', fontName='Pretendard', fontSize=11, leading=17, textColor=MUTED, wordWrap='CJK', spaceAfter=14),
    'h1': ParagraphStyle('h1', fontName='PretendardMedium', fontSize=20, leading=27, textColor=INK, wordWrap='CJK', spaceAfter=14),
    'h2': ParagraphStyle('h2', fontName='PretendardMedium', fontSize=12.2, leading=18, textColor=INK, wordWrap='CJK', spaceBefore=11, spaceAfter=6),
    'body': ParagraphStyle('body', fontName='Pretendard', fontSize=10, leading=15.5, textColor=INK, wordWrap='CJK', spaceAfter=7),
    'small': ParagraphStyle('small', fontName='Pretendard', fontSize=8.5, leading=12.7, textColor=MUTED, wordWrap='CJK', spaceAfter=5),
    'cell': ParagraphStyle('cell', fontName='Pretendard', fontSize=9, leading=13.5, textColor=INK, wordWrap='CJK'),
    'cellhead': ParagraphStyle('cellhead', fontName='PretendardMedium', fontSize=9, leading=13, textColor=INK, wordWrap='CJK'),
    'code': ParagraphStyle('code', fontName='Pretendard', fontSize=8.6, leading=13, textColor=INK, wordWrap='CJK', spaceAfter=0),
    'note': ParagraphStyle('note', fontName='PretendardMedium', fontSize=10, leading=15.2, textColor=BLUE, wordWrap='CJK'),
}

def P(text, style='body'):
    return Paragraph(text, styles[style])

def text(value):
    return escape(str(value))

def title(number, heading, sub):
    return [P(f'{number:02d} / {heading}', 'h1'), P(sub, 'subtitle')]

def table(rows, widths, header=True):
    data = [[P(text(value).replace('\n', '<br/>'), 'cellhead' if i == 0 and header else 'cell') for value in row] for i, row in enumerate(rows)]
    t = Table(data, colWidths=widths, hAlign='LEFT', repeatRows=1 if header else 0)
    commands = [
        ('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10), ('TOPPADDING', (0,0), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,-1), 9), ('LINEBELOW', (0,0), (-1,-1), 0.45, BORDER),
    ]
    if header:
        commands.append(('BACKGROUND', (0,0), (-1,0), PALE))
    for i in range(1 if header else 0, len(rows)):
        if i % 2 == 0:
            commands.append(('BACKGROUND', (0,i), (-1,i), LIGHT))
    t.setStyle(TableStyle(commands))
    return t

def box(content, color=PALE):
    t = Table([[P(content, 'note')]], colWidths=[WIDTH])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),color),('BOX',(0,0),(-1,-1),0.5,BORDER),
        ('LEFTPADDING',(0,0),(-1,-1),13),('RIGHTPADDING',(0,0),(-1,-1),13),
        ('TOPPADDING',(0,0),(-1,-1),11),('BOTTOMPADDING',(0,0),(-1,-1),11),
    ]))
    return t

def bullet(label, body):
    return P(f'<b>{label}</b>　{body}')

def code_block(code):
    lines = [Paragraph(escape(line).replace(' ', '&#160;'), styles['code']) for line in code.split('\n')]
    t = Table([[line] for line in lines], colWidths=[WIDTH])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),LIGHT),('LEFTPADDING',(0,0),(-1,-1),13),
        ('RIGHTPADDING',(0,0),(-1,-1),13),('TOPPADDING',(0,0),(-1,-1),0),
        ('BOTTOMPADDING',(0,0),(-1,-1),0),('TOPPADDING',(0,0),(0,0),11),
        ('BOTTOMPADDING',(0,-1),(0,-1),11),
    ]))
    return t

class Flow(Flowable):
    def __init__(self):
        Flowable.__init__(self)
        self.width, self.height = WIDTH, 70
    def draw(self):
        labels = [('Shopping Brain','카테고리·유형·예산'),('RAG 카탈로그','상품 정체성 확인'),('Commerce','옵션 가격·재고'),('Hybrid 검색','후보 정렬·리뷰 근거'),('AI 응답','조건·출처 유지')]
        gap = 13
        bw = (WIDTH - gap*4)/5
        for i,(a,b) in enumerate(labels):
            x=i*(bw+gap)
            self.canv.setFillColor(PALE if i != 2 else colors.HexColor('#EAF7F4'))
            self.canv.setStrokeColor(BORDER)
            self.canv.roundRect(x,8,bw,54,7,stroke=1,fill=1)
            self.canv.setFillColor(INK)
            self.canv.setFont('PretendardMedium',9.2)
            self.canv.drawCentredString(x+bw/2,41,a)
            self.canv.setFont('Pretendard',7.5)
            self.canv.setFillColor(MUTED)
            self.canv.drawCentredString(x+bw/2,23,b)
            if i<4:
                xx=x+bw+3
                self.canv.setStrokeColor(BLUE)
                self.canv.line(xx,35,xx+7,35)
                self.canv.line(xx+4,38,xx+7,35)
                self.canv.line(xx+4,32,xx+7,35)

def footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BLUE)
    canvas.rect(0,PAGE_H-9,PAGE_W,9,fill=1,stroke=0)
    canvas.setFont('PretendardMedium',8)
    canvas.setFillColor(MUTED)
    canvas.drawString(44,PAGE_H-34,'TOSS  /  RAG ENGINEERING NOTE')
    canvas.setFont('Pretendard',8)
    canvas.drawRightString(PAGE_W-44,PAGE_H-34,'2026.10.19  ·  팀 공유용')
    canvas.setStrokeColor(BORDER)
    canvas.line(44,44,PAGE_W-44,44)
    canvas.setFillColor(MUTED)
    canvas.setFont('Pretendard',7.7)
    canvas.drawString(44,29,'상태: 로컬 구현 · 운영 적용 및 개선 후 품질 평가는 미실행')
    canvas.drawRightString(PAGE_W-44,29,f'{doc.page} / 5')
    canvas.restoreState()

story=[]
# PAGE 1
story += [P('추천 품질 개선\n작업 정리'.replace('\n','<br/>'),'title'),
          P('구현 범위 · API 연동 · 데이터 보존 · 남은 검증', 'subtitle'),
          box('핵심: 상품 유형과 구매 조건으로 후보를 좁히고,<br/>상품 단위 검색·재정렬과 리뷰 근거 선택을 개선하는 코드를 작성했습니다.'),
          Spacer(1,11), P('현재 완료 범위', 'h2')]
story.append(table([
    ['구분','현재 상태'],
    ['로컬 구현','상품 유형 필터, 프로필 선택, 상품 단위 결합·재정렬, Commerce 조회, 리뷰 근거, 청커 v3'],
    ['확인한 내용','Python 문법 컴파일, 모듈 import, Git 공백 검사 및 정적 검토'],
    ['아직 진행하지 않은 내용','운영 API 교체, 기존 데이터 재청킹·재임베딩, 개선 후 추천 품질 평가, Brain E2E'],
    ['Git 반영','로컬 파일만 저장. 커밋·GitHub 푸시·main 병합 미실행'],
], [110,WIDTH-110]))
story += [P('전체 처리 흐름', 'h2'),Flow(),
          P('Shopping Brain은 사용자가 원하는 카테고리·상품 유형·예산을 구조화합니다. RAG는 상품 정체성을 확인하고, Commerce의 같은 옵션에서 가격·재고를 확인한 뒤 검색과 근거를 제공합니다.'),
          P('작업 위치', 'h2'),
          P('저장소: hongbinwee/codyssey-final-toss-backend<br/>브랜치: feature/rag-recommendation-quality','small'),
          P('원격 main에는 시작 시 README만 있어 실행 중인 RAG 서비스의 코드를 새 브랜치에 가져왔습니다. 기존 작업 디렉터리의 변경 사항은 덮어쓰지 않았습니다.','small'), PageBreak()]

# PAGE 2
story += title(2,'무엇을 개선했나','이전 탐색 평가에서 발견한 실패 사례를 바탕으로 작성한 변경입니다.')
story.append(table([
    ['기존에 확인한 문제','이번에 구현한 처리'],
    ['백팩 → 파우치, 선풍기 → 온열 안대가 1위','상품 유형 필터를 검색 전에 적용. 검수된 정규 유형과 주상품명으로 정체성을 판별'],
    ['동일 상품의 여러 청크가 후보 자리를 차지','각 채널에서 서로 다른 상품을 기본 50개까지 확보. 상품당 최대 3청크, 탐색 창 상한 2,000청크'],
    ['벡터·BM25 결합 후 올바른 상품의 순위 하락','상품별 채널 순위로 RRF 결합. 상품명·정체성 어휘 일치 후 상품 RRF 순으로 재정렬'],
    ['예산 초과·품절 후보가 최종 추천에 포함될 수 있음','Commerce에서 같은 옵션의 가격·재고를 함께 확인. 해당 유형의 전체 후보에 자격 조건 적용'],
    ['리뷰 전용 채널에서만 찾은 후보가 결과에서 제외','리뷰 전용 BM25·벡터 채널을 상품 결합과 근거 선택에 반영'],
    ['없는 상품 요청에도 무관한 상품 반환','유형/카탈로그 연결이 없으면 no_results 또는 low_relevance. 복수 유형이 모호하면 재질문 유도'],
], [178,WIDTH-178]))
story += [P('이전 평가의 참고 수치', 'h2')]
story.append(table([
    ['지표','개선 전 참고 결과','해석'],
    ['Hit@1','14/24 · 58.3%','첫 상품이 임시 정답 상품군에 속한 비율'],
    ['Hit@5','22/24 · 91.7%','상위 5개에 임시 정답이 하나 이상 포함'],
    ['Precision@5','55.8%','상위 5개에서 임시 정답이 차지한 비율'],
], [105,140,WIDTH-245]))
story += [Spacer(1,10),box('위 수치는 변경 전 평가입니다. 자동 상품군 라벨을 사용한 탐색 결과이며,<br/>이번 코드로 얼마나 개선됐는지는 아직 측정하지 않았습니다.'),
          P('현재 재정렬은 규칙 기반입니다. 별도 cross-encoder나 새 임베딩 모델은 도입하지 않았습니다. 오탈자·별칭 누락·묶음 상품·원본 오분류는 후속 검증이 필요합니다.','small'),PageBreak()]

# PAGE 3
story += title(3,'Shopping Brain 연동','기존 POST /v1/rag/search 경로를 유지하고 선택적 필드를 추가했습니다.')
story.append(code_block('''{
  "request_id": "backpack-001",
  "original_question": "통학용 5만원 이하 백팩 추천",
  "query": "통학용 백팩",
  "category": "fashion",
  "profile": "test_items2",
  "product_type": "backpack",
  "filters": {
    "price_max": 50000,
    "currency": "KRW",
    "in_stock": true
  },
  "top_k": 5
}'''))
story += [P('추가 요청 필드', 'h2')]
story.append(table([
    ['필드','처리 기준'],
    ['profile','생략하면 서버 기본 프로필. 허용 목록 밖의 값은 unsupported_profile(422)'],
    ['product_type','Brain이 판정한 유형 ID/이름. 검수된 정규 유형과 편집 가능한 별칭 목록으로 확장'],
    ['filters.in_stock','생략 시 서버 정책(기본 true). false를 명시하면 품절을 포함한 탐색 허용'],
], [125,WIDTH-125]))
story += [P('응답에서 확인할 정보', 'h2'),
          bullet('profile_name / search_context','실제 프로필, 유형 판정 경로, 후보 수와 빈 결과의 이유.'),
          bullet('items[].commerce','선택한 variant_id, 그 옵션의 원화 가격·재고, 조회 시각과 원본 스키마.'),
          bullet('items[].ranking / evidence','어휘 일치·검색 순위와 원문/출처/offset, 리뷰 전용 채널 순위.'),
          P('가격은 최상위 max_price가 아닌 filters.price_max로 전달합니다. 가격 범위에는 currency가 필요하며 현재 KRW만 지원합니다. 엄격한 응답 모델을 쓰는 팀은 추가 필드를 반영해야 합니다.','small'),
          box('ok 응답도 모든 조건 충족을 뜻하지 않습니다.<br/>unverified_conditions가 있으면 Brain이 미검증 조건을 설명하거나 추가 질문해야 합니다.'),PageBreak()]

# PAGE 4
story += title(4,'DB · 리뷰 · 청킹','기존 원본과 색인을 보존하면서 새 코드의 적용 지점을 구분했습니다.')
story.append(table([
    ['구분','연결/대상','이번 작업의 상태'],
    ['상품·옵션 원본','5432 / toss / test_items2\nproducts, product_variants, reviews','원본 데이터 및 상품·리뷰 ID 유지'],
    ['청크·임베딩','5432 / toss_rag / rag\n프로필 test_items2','기존 색인 유지. 새 청킹 코드로 재생성하지 않음'],
    ['새 배포 설정 예시','RAG_DEFAULT_PROFILE=test_items2\nRAG_ALLOWED_PROFILES=test_items2,all_products','설정 예시만 작성. 현재 서비스 설정 변경 아님'],
], [100,215,WIDTH-315]))
story += [P('기존 데이터 규모 — 적재·색인 보고서 기준', 'h2'),
          P('<b>상품 1,500개 · 옵션 1,917개 · 리뷰 46,100개 · 청크 114,106개</b><br/>리뷰: REAL 41,523개 / SYNTHETIC 4,577개. 이 PDF를 만들면서 DB를 새로 집계한 수치는 아닙니다.'),
          P('가격·재고 검증', 'h2'),
          bullet('옵션 일관성','예산과 재고를 동일 옵션에서 검사하고, 조건을 만족하는 옵션 중 최저가·ID 순으로 하나를 선택합니다. 표시 가격도 그 옵션의 값으로 맞춥니다.'),
          bullet('읽기 전용','Commerce 조회는 READ ONLY 트랜잭션과 5초 쿼리 제한을 사용합니다. 설정/권한이 부족하면 검증된 상품처럼 반환하지 않습니다.'),
          P('조회 값은 현재 DB 행을 기준으로 합니다. 외부 쇼핑몰의 실시간 판매가를 보장하지 않으며, 관측/CANDIDATE·시뮬레이션 정보를 유지합니다. 주문 시 재고 확인은 별도로 필요합니다.','small'),
          P('리뷰 근거 및 청커 v3', 'h2'),
          bullet('근거 선택','관리용 필드와 지나치게 짧은 리뷰 조각을 제외하고, 동일 리뷰가 근거를 독점하지 않게 합니다. 실제 리뷰를 합성 리뷰보다 우선합니다.'),
          bullet('새 청킹 코드','관리용 ID·수집/평가 통계를 임베딩 본문에서 제외합니다. 짧은 꼬리 조각은 합치거나 경계를 조정하고, 원문·offset·토큰 상한을 유지합니다.'),
          box('청커 v3는 코드만 작성됐습니다.<br/>기존 114,106개 청크에 적용하려면 별도 run 생성·검증 후 프로필 전환이 필요합니다.'),
          P('기존 /v1/catalog/test-items 목록은 all_products의 예전 데이터에 계속 고정됩니다. 새 test_items2 검색 결과와 같은 목록으로 해석하면 안 됩니다.','small'),PageBreak()]

# PAGE 5
story += title(5,'검증 상태와 다음 작업','구현 완료, 실행 적용, 품질 확인을 구분해 팀에 전달합니다.')
story.append(table([
    ['항목','상태','의미'],
    ['문법 컴파일 / 모듈 import','확인','파이썬 코드의 문법과 의존 모듈 로딩 확인'],
    ['Git 공백 검사 / 정적 검토','확인','코드·문서를 읽고 구조와 변경 범위를 점검'],
    ['자동 테스트 / 검색 품질 재평가','미실행','실제 동작·회귀·개선 폭을 입증한 상태는 아님'],
    ['운영 API 교체 / Brain E2E','미실행','현재 사용자가 호출하는 서비스는 아직 이 코드가 아님'],
    ['재청킹 / 재임베딩 / Git 공유','미실행','기존 데이터 유지. 커밋·푸시·main 반영 전'],
], [190,62,WIDTH-252]))
story += [P('다음 적용 순서', 'h2'),
          bullet('1. 연동 계약 반영','Brain이 category·product_type·가격 필터를 전달하고, 응답의 Commerce 검증 및 미검증 조건을 처리하도록 연결합니다.'),
          bullet('2. 설정·조회 권한 확인','기존 5432 연결에서 RAG/Commerce 계정과 허용 프로필·스키마를 확인합니다. 새 DB나 포트를 만들 필요는 없습니다.'),
          bullet('3. 검색·통합 평가','사람이 검수한 정답과 독립 holdout으로 이전 Hybrid와 비교합니다. 상품 유형·목록 밖 요청·예산/재고·리뷰 출처·p95 지연을 함께 확인합니다.'),
          bullet('4. 운영 반영 및 청킹 전환','검증된 코드의 배포와 청커 v3 색인 전환을 구분해 진행합니다. 기존 run을 보존해 되돌릴 수 있게 합니다.'),
          P('팀별 확인 사항', 'h2'),
          P('<b>Brain팀</b>: 유형/필터 전달, 빈 결과·미검증 조건 처리, 최종 답변 근거 유지.<br/><b>DB팀</b>: source_dataset → 스키마 매핑, 조회 계정 권한, 옵션 가격·재고 의미 확인.<br/><b>RAG팀</b>: 유형 정답 검수, 후보 수·지연·근거 품질 평가, 코드/색인 버전 구분.'),
          P('구현 자료', 'h2'),
          P('docs/rag-recommendation-quality.md<br/>contracts/product-rag/v0.3/request.schema.json<br/>deploy/product-rag-runtime.env.example<br/>src/toss_ads/rag/{intent,retriever,commerce,chunker,api}.py','small'),
          P('자료 근거: 로컬 구현 코드/문서, data/test_items2/index_report.json, load_report.json, search_quality_2026-10-19.md. 이 PDF 작성 중 추가 배포·DB 변경·품질 평가를 수행하지 않았습니다.','small')]

# Values on page 4 must agree with the existing export/load reports.
index = json.loads((ROOT / 'data/test_items2/index_report.json').read_text())
if (index['counts']['product_count'], index['counts']['review_count'], index['counts']['chunk_count']) != (1500,46100,114106):
    raise ValueError('Source report changed: update the PDF snapshot text')

doc = SimpleDocTemplate(str(OUT), pagesize=A4, rightMargin=44, leftMargin=44,
                        topMargin=57, bottomMargin=59,
                        title='추천 품질 개선 작업 정리 | 2026-10-19',
                        author='Toss RAG Engineering',
                        subject='로컬 구현 범위, Brain 연동 계약, 데이터 보존 및 검증 상태',
                        pageCompression=1)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
print(f'{OUT.stat().st_size:,} bytes')
