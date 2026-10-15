"""API snapshot -> 상품/리뷰 단위의 원문 추적 가능한 검색 문서."""
import math
from decimal import Decimal, InvalidOperation
from urllib.parse import quote, urlencode

from .io import digest
from .client import APIClient
from .text import tokenize

REQUIRED_FIELDS = ('product_id', 'document_id', 'document_type', 'title', 'brand',
                   'category', 'price', 'text', 'source_id')


def nonempty_id(value):
    return isinstance(value, str) and bool(value.strip())


def preprocess(raw, mappings=None):
    if (not isinstance(raw, dict) or raw.get('schema_version') != 'amazon-snapshot-v1'
            or not nonempty_id(raw.get('dataset_version'))
            or raw.get('source_kind') not in ('REAL', 'SYNTHETIC')
            or any(not isinstance(raw.get(k), list) for k in ('products', 'reviews'))):
        raise ValueError('amazon-snapshot-v1, dataset_version, source_kind, products/reviews 배열이 필요합니다.')
    APIClient(raw.get('base_url'))
    mapping = {}
    if mappings is not None:
        if not isinstance(mappings, list): raise ValueError('mapping은 배열이어야 합니다.')
        for item in mappings:
            if not isinstance(item, dict) or any(not nonempty_id(item.get(k)) for k in
                                                ('category', 'parent_asin', 'commerce_product_id')):
                raise ValueError('mapping 필수 필드가 누락됐습니다.')
            key = (item['category'], item['parent_asin'])
            if key in mapping: raise ValueError('중복 상품 mapping입니다.')
            mapping[key] = item['commerce_product_id']
    report = {'schema_version': 'preprocess-report-v1', 'dataset_version': raw['dataset_version'],
              'input_products': len(raw['products']), 'input_reviews': len(raw['reviews']),
              'rejected': [], 'warnings': [], 'missing_fields': []}
    products, documents, seen_reviews = {}, [], set()

    def event(list_name, location, reason, field=None):
        item = {'location': location, 'reason': reason}
        if field: item['field'] = field
        report[list_name].append(item)

    def text(value, location, field):
        if value is None or value == '':
            event('missing_fields', location, '값 없음; 빈 문자열 유지', field)
            return ''
        if not isinstance(value, str):
            event('warnings', location, '문자열 아님; 빈 문자열 처리', field)
            return ''
        return value

    def text_list(value, location, field):
        if value is None: return []
        if isinstance(value, str): return [value] if value.strip() else []
        if not isinstance(value, list):
            event('warnings', location, '문자열 배열 아님; 검색 본문에서 제외', field)
            return []
        result = [s for s in value if isinstance(s, str) and s.strip()]
        if len(result) < len(value):
            event('warnings', location, '빈 값/문자열 아닌 배열 항목 제외', field)
        return result

    def entry(item, collection, row):
        location = f'/{collection}/{row}/record'
        if (not isinstance(item, dict) or not nonempty_id(item.get('category'))
                or not isinstance(item.get('record'), dict)):
            raise ValueError(location + ': category와 record 객체가 필요합니다.')
        if 'user_id' in item['record']:
            raise ValueError(location + ': API 계약에 없는 user_id가 포함됐습니다.')
        return item['category'], item['record'], location

    def make(product, record, kind, sid, body, location):
        category, asin = product['category'], product['product_id']
        endpoint = raw.get('base_url', '').rstrip('/') + '/v1/categories/' + quote(category, safe='')
        url = endpoint + '/products/' + quote(asin, safe='') if kind == 'product' else endpoint + '/reviews?' + urlencode({'parent_asin': asin})
        return {'product_id': asin,
                'document_id': ':'.join(quote(v, safe='') for v in ('amazon', category, kind, asin, sid)),
                'document_type': kind, 'title': product['title'], 'brand': product['brand'],
                'category': category, 'price': product['price'], 'text': body, 'source_id': sid,
                'currency': 'USD', 'price_basis': 'dataset_crawl_time',
                'source_kind': raw['source_kind'], 'source_ref': url,
                'source_locator': location, 'source_hash': digest(record),
                'dataset_version': raw['dataset_version'],
                'parent_asin': asin, 'asin': record.get('asin') if isinstance(record.get('asin'), str) else None,
                'commerce_product_id': mapping.get((category, asin)), 'variant_id': None}

    for row, item in enumerate(raw['products']):
        category, record, location = entry(item, 'products', row)
        asin = record.get('parent_asin')
        if not nonempty_id(asin):
            event('rejected', location, 'parent_asin 누락/형식 오류')
            continue
        key = (category, asin)
        if key in products: raise ValueError(location + ': 같은 category 내 중복 parent_asin')
        title = text(record.get('title'), location, 'title')
        details = record.get('details')
        if details is None: details = {}
        if not isinstance(details, dict):
            event('warnings', location, 'details 객체 아님; 스펙 제외', 'details')
            details = {}
        brand = text(details.get('Brand'), location, 'details.Brand')
        original_price = record.get('price')
        price = None
        if original_price is None or original_price == '':
            event('missing_fields', location, '가격 없음; null 유지', 'price')
        else:
            try:
                if isinstance(original_price, bool) or not isinstance(original_price, (str, int, float)):
                    raise ValueError()
                number = Decimal(str(original_price))
                if not number.is_finite() or number < 0: raise ValueError()
                price = float(number)
                if not math.isfinite(price): raise ValueError()
            except (InvalidOperation, ValueError, OverflowError):
                price = None
                event('warnings', location, '유효한 USD 숫자 아님; null 처리', 'price')
        product = {'product_id': asin, 'title': title, 'brand': brand, 'category': category, 'price': price}
        products[key] = product
        detail_lines = [f'{k}: {v}' for k, v in sorted(details.items())
                        if isinstance(v, (str, int, float)) and not isinstance(v, bool)]
        parts = [title, brand, record.get('main_category', ''),
                 *text_list(record.get('features'), location, 'features'),
                 *text_list(record.get('description'), location, 'description'), *detail_lines]
        body = '\n'.join(p for p in parts if isinstance(p, str) and p.strip())
        if tokenize(body): documents.append(make(product, record, 'product', asin, body, location))
        else: event('rejected', location, '상품 검색 본문 없음; 리뷰 연결용 메타데이터 유지')

    for row, item in enumerate(raw['reviews']):
        category, record, location = entry(item, 'reviews', row)
        asin, rid = record.get('parent_asin'), record.get('review_key')
        if not nonempty_id(asin) or not nonempty_id(rid):
            event('rejected', location, 'parent_asin/review_key 누락/형식 오류')
            continue
        key, review_key = (category, asin), (category, rid)
        if key not in products:
            event('rejected', location, '같은 category의 연결 상품 없음')
            continue
        if review_key in seen_reviews:
            event('rejected', location, 'category 내 중복 review_key; 첫 유효 리뷰 유지')
            continue
        body = text(record.get('text'), location, 'text')
        if not body.strip():
            event('rejected', location, '리뷰 본문 없음')
            continue
        if not tokenize(body):
            event('rejected', location, '검색 가능한 단어 없음; 원본 snapshot은 보존')
            continue
        seen_reviews.add(review_key)
        doc = make(products[key], record, 'review', rid, body, location)
        doc['review_title'] = text(record.get('title'), location, 'title')
        for name in ('rating', 'timestamp', 'verified_purchase'):
            doc[name] = record.get(name)
        documents.append(doc)
    report.update(output_documents=len(documents),
                  output_products=sum(d['document_type'] == 'product' for d in documents),
                  output_reviews=sum(d['document_type'] == 'review' for d in documents),
                  commerce_mapping_missing=sum(d['commerce_product_id'] is None for d in documents))
    return documents, report


def verify_documents(raw, documents, mappings=None):
    expected, _ = preprocess(raw, mappings)
    if documents != expected:
        raise ValueError('documents가 원본 snapshot/매핑으로 생성한 결과와 다릅니다.')
    if len({d['document_id'] for d in documents}) != len(documents):
        raise ValueError('document_id 중복입니다.')
    return {'status': 'ok', 'verified_documents': len(documents),
            'verified_reviews': sum(d['document_type'] == 'review' for d in documents),
            'dataset_version': raw['dataset_version']}
