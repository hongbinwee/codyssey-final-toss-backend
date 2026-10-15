"""명세의 GET 엔드포인트만 호출하는 작은 읽기 전용 client."""
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from .io import decode_json

DEFAULT_URL = os.environ.get('AMAZON_API_BASE_URL', '')
CATEGORIES = ('Appliances', 'Clothing_Shoes_and_Jewelry', 'Grocery_and_Gourmet_Food')


class APIError(RuntimeError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


class APIClient:
    def __init__(self, base_url=DEFAULT_URL, timeout=20, retries=2):
        if not isinstance(base_url, str): raise ValueError('base_url은 문자열이어야 합니다.')
        parsed = urllib.parse.urlsplit(base_url)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment):
            raise ValueError('base_url은 인증정보/query/fragment가 없는 http(s) URL이어야 합니다.')
        if timeout <= 0 or not isinstance(retries, int) or not 0 <= retries <= 3:
            raise ValueError('timeout > 0, retries 0..3이어야 합니다.')
        self.base_url, self.timeout, self.retries = base_url.rstrip('/'), timeout, retries
        self.dataset_version = None

    def get(self, path, params=None):
        if not path.startswith('/') or path.startswith('//'):
            raise ValueError('상대 API 경로가 필요합니다.')
        url = self.base_url + path
        if params: url += '?' + urllib.parse.urlencode(params)
        for attempt in range(self.retries + 1):
            try:
                request = urllib.request.Request(url, headers={'Accept': 'application/json',
                                                                'User-Agent': 'gaon-rag/1.0'})
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    if response.geturl().split('?')[0] != url.split('?')[0]:
                        raise APIError('UNEXPECTED_REDIRECT', '예상하지 않은 리다이렉트입니다.')
                    # shortcut: 소규모 페이지 JSON용, 더 큰 응답은 streaming parser로 전환.
                    data = response.read(10 * 1024 * 1024 + 1)
                    if len(data) > 10 * 1024 * 1024:
                        raise APIError('RESPONSE_TOO_LARGE', 'API 페이지가 10MiB를 초과했습니다.')
                    try:
                        result = decode_json(data)
                    except (UnicodeError, ValueError) as exc:
                        raise APIError('INVALID_JSON', 'API가 JSON을 반환하지 않았습니다.') from exc
                    if not isinstance(result, dict):
                        raise APIError('INVALID_RESPONSE', 'API 응답은 객체여야 합니다.')
                    return result
            except urllib.error.HTTPError as exc:
                if exc.code == 403:
                    raise APIError('ACCESS_DENIED', '403: NPM Access List에 실행 환경 IP 허용이 필요합니다.') from exc
                if exc.code not in (429, 502, 503, 504) or attempt == self.retries:
                    raise APIError('HTTP_' + str(exc.code), 'API 요청 실패: HTTP ' + str(exc.code)) from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if attempt == self.retries:
                    raise APIError('NETWORK_ERROR', 'API 네트워크/DNS/시간 초과 오류입니다.') from exc
            time.sleep(0.5 * (2 ** attempt))
        raise APIError('NETWORK_ERROR', '요청을 완료하지 못했습니다.')

    def check_version(self, page):
        version = page.get('dataset_version')
        if not isinstance(version, str) or not version.strip():
            raise APIError('INVALID_RESPONSE', 'dataset_version 누락입니다.')
        if self.dataset_version is None: self.dataset_version = version
        if version != self.dataset_version:
            raise APIError('DATASET_CHANGED', '조회 중 dataset_version이 바뀌었습니다. 처음부터 다시 수집하세요.')

    def pages(self, path, params=None, limit=200, max_items=None):
        if not isinstance(limit, int) or not 1 <= limit <= 200:
            raise ValueError('page limit은 1..200입니다.')
        if max_items is not None and (not isinstance(max_items, int) or max_items < 1):
            raise ValueError('max_items는 양의 정수입니다.')
        offset, emitted, initial_total = 0, 0, None
        while True:
            size = min(limit, max_items - emitted) if max_items else limit
            page = self.get(path, {**(params or {}), 'limit': size, 'offset': offset})
            self.check_version(page)
            items, total = page.get('items'), page.get('total')
            if (not isinstance(items, list) or type(total) is not int or total < 0
                    or type(page.get('offset')) is not int or page['offset'] != offset
                    or type(page.get('limit')) is not int or page['limit'] != size
                    or len(items) != min(size, max(0, total - offset))
                    or any(not isinstance(item, dict) for item in items)):
                raise APIError('INVALID_PAGE', '페이지 필드/개수/offset/limit이 명세와 다릅니다.')
            if initial_total is None: initial_total = total
            if total != initial_total:
                raise APIError('DATASET_CHANGED', '페이지 조회 중 total이 변경되었습니다.')
            for item in items:
                yield item
                emitted += 1
            offset += size
            if offset >= total or (max_items is not None and emitted >= max_items): break

    def snapshot(self, categories=CATEGORIES, products_per_category=10):
        if not isinstance(products_per_category, int) or not 1 <= products_per_category <= 10000:
            raise ValueError('products_per_category는 1..10000입니다.')
        categories = list(categories)
        if not categories or len(categories) != len(set(categories)) or any(c not in CATEGORIES for c in categories):
            raise ValueError('유효하고 중복되지 않은 category를 지정하세요.')
        self.check_version(self.get('/healthz'))
        raw = {'schema_version': 'amazon-snapshot-v1', 'dataset_version': self.dataset_version,
               'source_kind': 'REAL', 'base_url': self.base_url,
               'fetched_at': datetime.now(timezone.utc).isoformat(), 'categories': categories,
               'sampling': {'products_per_category': products_per_category,
                            'method': 'API parent_asin 정렬의 앞 N개; 무작위 표본이 아님',
                            'review_scope': '선택 상품의 API 선별 리뷰 전부; 원본 전체 리뷰 아님'},
               'products': [], 'reviews': []}
        for category in categories:
            root = '/v1/categories/' + urllib.parse.quote(category, safe='')
            seen = set()
            for product in self.pages(root + '/products', max_items=products_per_category):
                asin = product.get('parent_asin')
                if not isinstance(asin, str) or not asin.strip() or asin in seen:
                    raise APIError('INVALID_PRODUCT_ID', '상품 parent_asin 누락/중복입니다.')
                seen.add(asin)
                raw['products'].append({'category': category, 'record': product})
                for review in self.pages(root + '/reviews', {'parent_asin': asin}):
                    if review.get('parent_asin') != asin or 'user_id' in review:
                        raise APIError('INVALID_REVIEW', '리뷰 상품 연결 또는 user_id 제거 계약 위반입니다.')
                    raw['reviews'].append({'category': category, 'record': review})
        return raw
