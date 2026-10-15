"""rank-bm25 색인과 JSON 저장/복원. 검색 함수는 handoff 검증용 기본 구현."""
import copy
import importlib.metadata
import math
import re

from rank_bm25 import BM25Okapi

from .io import digest, read_json, write_json
from .preprocess import REQUIRED_FIELDS
from .text import TOKENIZER_VERSION, tokenize


class BM25Index:
    def __init__(self, documents):
        if not isinstance(documents, list) or not documents:
            raise ValueError('유효 문서가 하나 이상 필요합니다.')
        self.documents = copy.deepcopy(documents)
        seen = set()
        for document in self.documents:
            if not isinstance(document, dict) or any(k not in document for k in REQUIRED_FIELDS):
                raise ValueError('document 필수 필드가 없습니다.')
            if document['document_type'] not in ('product', 'review'):
                raise ValueError('document_type은 product/review여야 합니다.')
            for key in ('document_id', 'product_id', 'source_id', 'category', 'dataset_version',
                        'source_ref', 'source_locator'):
                if not isinstance(document.get(key), str) or not document[key].strip():
                    raise ValueError(key + '는 비어 있지 않은 문자열이어야 합니다.')
            for key in ('title', 'brand', 'text'):
                if not isinstance(document[key], str): raise ValueError(key + '는 문자열이어야 합니다.')
            price = document['price']
            if price is not None and (isinstance(price, bool) or not isinstance(price, (int, float))
                                      or not math.isfinite(price) or price < 0):
                raise ValueError('price는 null 또는 음이 아닌 유한한 숫자여야 합니다.')
            if (document.get('source_kind') not in ('REAL', 'SYNTHETIC')
                    or document.get('currency') != 'USD'
                    or not isinstance(document.get('source_hash'), str)
                    or not re.fullmatch('[a-f0-9]{64}', document['source_hash'])):
                raise ValueError('source_kind/currency/source_hash 형식이 잘못됐습니다.')
            if document['document_id'] in seen: raise ValueError('중복 document_id입니다.')
            seen.add(document['document_id'])
        self.tokens = [tokenize(d['text']) for d in self.documents]
        if any(not tokens for tokens in self.tokens):
            raise ValueError('토큰이 없는 문서가 있습니다. 전처리 보고서를 확인하세요.')
        self.model = BM25Okapi(self.tokens, k1=1.5, b=0.75, epsilon=0.25)

    def state(self):
        return {key: getattr(self.model, key) for key in
                ('k1', 'b', 'epsilon', 'corpus_size', 'avgdl', 'doc_len', 'doc_freqs', 'idf', 'average_idf')}

    def save(self, path):
        payload = {'schema_version': 'bm25-index-v1', 'tokenizer_version': TOKENIZER_VERSION,
                   'library': 'rank-bm25', 'library_version': importlib.metadata.version('rank-bm25'),
                   'documents': self.documents, 'tokens': self.tokens, 'state': self.state()}
        write_json(path, {**payload, 'sha256': digest(payload)})

    @classmethod
    def load(cls, path):
        payload = read_json(path)
        if not isinstance(payload, dict): raise ValueError('색인은 JSON 객체여야 합니다.')
        signature = payload.pop('sha256', None)
        if signature != digest(payload): raise ValueError('색인 내용 hash가 일치하지 않습니다.')
        if (payload.get('schema_version') != 'bm25-index-v1'
                or payload.get('tokenizer_version') != TOKENIZER_VERSION
                or payload.get('library') != 'rank-bm25'
                or payload.get('library_version') != importlib.metadata.version('rank-bm25')):
            raise ValueError('색인 schema/tokenizer/library 버전이 다릅니다. 다시 구축하세요.')
        # JSON에는 문서/토큰/통계를 저장하고 동일 library로 객체를 재구성한다. pickle 실행 없음.
        instance = cls(payload.get('documents'))
        if instance.tokens != payload.get('tokens') or instance.state() != payload.get('state'):
            raise ValueError('저장된 토큰/통계가 문서와 일치하지 않습니다.')
        return instance

    def search(self, query, top_k=5, document_type=None, category=None, product_id=None,
               min_query_coverage=0.5):
        tokens = list(dict.fromkeys(tokenize(query)))
        if not tokens or len(query) > 2000: raise ValueError('검색 질문은 1..2000자, 유효 단어가 필요합니다.')
        if type(top_k) is not int or not 1 <= top_k <= 100: raise ValueError('top_k는 1..100입니다.')
        if document_type not in (None, 'product', 'review'): raise ValueError('document_type 오류입니다.')
        if (isinstance(min_query_coverage, bool) or not isinstance(min_query_coverage, (int, float))
                or not math.isfinite(min_query_coverage) or not 0 <= min_query_coverage <= 1):
            raise ValueError('min_query_coverage는 0..1입니다.')
        for value in (category, product_id):
            if value is not None and not isinstance(value, str): raise ValueError('필터는 문자열이어야 합니다.')
        scores = self.model.get_scores(tokens)
        matches = []
        for document, terms, score in zip(self.documents, self.tokens, scores):
            if document_type and document['document_type'] != document_type: continue
            if category and document['category'] != category: continue
            if product_id and document['product_id'] != product_id: continue
            matched = sorted(set(tokens).intersection(terms))
            if not matched: continue
            if not math.isfinite(float(score)): raise ValueError('BM25 점수가 유한하지 않습니다.')
            coverage = len(matched) / len(tokens)
            matches.append({**copy.deepcopy(document), 'score': float(score), 'matched_terms': matched,
                            'query_coverage': coverage, 'evidence_sufficient': coverage >= min_query_coverage})
        # rank-bm25는 작은 corpus에서 IDF가 0/음수일 수 있어 score>0으로 필터링하지 않는다.
        matches.sort(key=lambda d: (not d['evidence_sufficient'], -d['score'], d['document_id']))
        results = matches[:top_k]
        status = ('no_results' if not matches else 'ok' if any(r['evidence_sufficient'] for r in results)
                  else 'insufficient_evidence')
        return {'schema_version': 'rag-result-v1', 'status': status, 'query': query,
                'method': 'BM25Okapi', 'results': results, 'matched_document_count': len(matches),
                'min_query_coverage': min_query_coverage,
                'dataset_versions': sorted({d['dataset_version'] for d in self.documents}),
                'limitations': ['단어 일치 점수이며 의미적 관련성·사실 검증 결과가 아닙니다.',
                                '원본 USD 가격은 수집 시점 값이며 현재 쇼핑몰 구매 가격이 아닙니다.']}
