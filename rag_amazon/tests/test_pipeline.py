import json
import tempfile
import unittest
from pathlib import Path

from rag_amazon.preprocess import preprocess, verify_documents
from rag_amazon.index import BM25Index, tokenize
from rag_amazon.client import APIClient, APIError


def snapshot():
    return {'schema_version': 'amazon-snapshot-v1', 'dataset_version': 'test-version',
            'source_kind': 'SYNTHETIC', 'base_url': 'https://example.invalid',
            'categories': ['Appliances'],
            'products': [{'category': 'Appliances', 'record': {
                'parent_asin': 'A1', 'title': 'Coffee maker', 'price': '19.99',
                'features': ['Reusable filter'], 'description': ['Makes hot coffee'],
                'details': {'Brand': 'Acme'}}}],
            'reviews': [{'category': 'Appliances', 'record': {
                'review_key': 'r1', 'parent_asin': 'A1', 'text': '  Excellent coffee filter.\n',
                'title': 'Great', 'rating': 5}}]}


class PreprocessTests(unittest.TestCase):
    def test_real_schema_ids_evidence_price(self):
        raw = snapshot()
        docs, report = preprocess(raw)
        self.assertEqual(len(docs), 2)
        self.assertEqual(docs[1]['text'], raw['reviews'][0]['record']['text'])
        self.assertEqual(docs[1]['source_id'], 'r1')
        self.assertEqual(docs[1]['product_id'], 'A1')
        self.assertEqual(docs[1]['brand'], 'Acme')
        self.assertEqual(docs[1]['price'], 19.99)
        self.assertEqual(docs[1]['currency'], 'USD')
        self.assertIsNone(docs[1]['commerce_product_id'])
        self.assertEqual(report['rejected'], [])
        self.assertEqual(verify_documents(raw, docs)['verified_documents'], 2)

    def test_category_is_part_of_identity(self):
        raw = snapshot()
        raw['products'].append({'category': 'Grocery_and_Gourmet_Food', 'record': {
            'parent_asin': 'A1', 'title': 'Beans'}})
        docs, _ = preprocess(raw)
        self.assertEqual(len({d['document_id'] for d in docs}), 3)
        self.assertEqual(docs[-1]['brand'], 'Acme')
        self.assertNotEqual(docs[0]['document_id'], docs[1]['document_id'])

    def test_missing_and_orphan_and_duplicate(self):
        raw = snapshot()
        raw['products'][0]['record']['price'] = 'unavailable'
        raw['reviews'] += [raw['reviews'][0], {'category': 'Appliances', 'record': {
            'review_key': 'r2', 'parent_asin': 'unknown', 'text': 'X'}},
            {'category': 'Appliances', 'record': {'parent_asin': 'A1', 'text': 'X'}},
            {'category': 'Appliances', 'record': {'review_key': 'r3', 'parent_asin': 'A1', 'text': ' '}}]
        docs, report = preprocess(raw)
        self.assertEqual(len(docs), 2)
        self.assertIsNone(docs[0]['price'])
        self.assertEqual(len(report['rejected']), 4)
        self.assertTrue(report['warnings'])

    def test_duplicate_product_and_pii_rejected(self):
        raw = snapshot()
        raw['products'].append(raw['products'][0])
        with self.assertRaises(ValueError): preprocess(raw)
        raw = snapshot()
        raw['reviews'][0]['record']['user_id'] = 'should-not-be-returned'
        with self.assertRaises(ValueError): preprocess(raw)

    def test_tampered_evidence_fails(self):
        raw = snapshot()
        docs, _ = preprocess(raw)
        docs[1]['text'] = 'invented quote'
        with self.assertRaises(ValueError): verify_documents(raw, docs)

    def test_mapping_is_optional_and_validated(self):
        raw = snapshot()
        mapping = [{'category': 'Appliances', 'parent_asin': 'A1', 'commerce_product_id': 'p-real'}]
        docs, _ = preprocess(raw, mapping)
        self.assertTrue(all(d['commerce_product_id'] == 'p-real' for d in docs))
        with self.assertRaises(ValueError): preprocess(raw, mapping + mapping)


class IndexTests(unittest.TestCase):
    def test_search_roundtrip_and_provenance(self):
        docs, _ = preprocess(snapshot())
        index = BM25Index(docs)
        before = index.search('coffee filter', document_type='review')
        self.assertEqual(before['status'], 'ok')
        self.assertEqual(before['results'][0]['source_id'], 'r1')
        self.assertEqual(before['results'][0]['text'], docs[1]['text'])
        self.assertEqual(before['results'][0]['query_coverage'], 1.0)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'index.json'
            index.save(path)
            loaded = BM25Index.load(path)
            self.assertEqual(loaded.search('coffee filter', document_type='review'), before)
            data = json.loads(path.read_text())
            data['documents'][0]['text'] = 'tampered'
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError): BM25Index.load(path)

    def test_no_results_vs_weak_vs_bad_query(self):
        docs, _ = preprocess(snapshot())
        index = BM25Index(docs)
        self.assertEqual(index.search('waterproof')['status'], 'no_results')
        self.assertEqual(index.search('coffee waterproof swimming')['status'], 'insufficient_evidence')
        with self.assertRaises(ValueError): index.search('!!!')
        with self.assertRaises(ValueError): index.search('coffee', top_k=0)
        self.assertEqual(index.search('coffee', category='missing')['status'], 'no_results')

    def test_shared_tokenizer_and_finite_scores(self):
        self.assertEqual(tokenize('Café COFFEE  필터!'), ['café', 'coffee', '필터'])
        docs, _ = preprocess(snapshot())
        self.assertTrue(all(isinstance(r['score'], float) for r in BM25Index(docs).search('coffee')['results']))

    def test_reject_duplicate_docs_and_empty_tokens(self):
        docs, _ = preprocess(snapshot())
        with self.assertRaises(ValueError): BM25Index(docs + [docs[0]])
        docs[0]['text'] = '!!!'
        with self.assertRaises(ValueError): BM25Index([docs[0]])


class ClientTests(unittest.TestCase):
    def test_pages_and_version(self):
        client = APIClient('https://example.invalid')
        def request(path, params=None):
            offset = params['offset']
            return {'dataset_version': 'v1', 'items': [{'n':offset}], 'limit':1,
                    'offset':offset, 'total':2}
        client.get = request
        self.assertEqual(list(client.pages('/x', limit=1)), [{'n':0}, {'n':1}])
        client.get = lambda *a, **k: {'dataset_version':'v2', 'items':[], 'limit':1, 'offset':0, 'total':0}
        with self.assertRaises(APIError): list(client.pages('/x', limit=1))

    def test_bad_page_must_not_silently_truncate(self):
        for response in ({'dataset_version':'v1','items':[], 'limit':1,'offset':0,'total':2},
                         {'dataset_version':'v1','items':[{}], 'limit':1,'offset':10,'total':2}):
            client = APIClient('https://example.invalid')
            client.get = lambda *a, **k: response
            with self.assertRaises(APIError): list(client.pages('/x',limit=1))

    def test_bad_urls(self):
        for url in ('http://user:password@example.com','ftp://example.com', 'https://example.com?token=x'):
            with self.assertRaises(ValueError): APIClient(url)



class MoreBoundaryTests(unittest.TestCase):
    def test_huge_price_becomes_null(self):
        raw = snapshot()
        raw['products'][0]['record']['price'] = '1e999'
        docs, _ = preprocess(raw)
        self.assertIsNone(docs[0]['price'])

    def test_http_403_no_retry_and_503_retry(self):
        from unittest.mock import patch
        from urllib.error import HTTPError
        client = APIClient('https://example.invalid', retries=2)
        with patch('urllib.request.urlopen', side_effect=HTTPError('u',403,'Denied',{},None)) as call:
            with self.assertRaises(APIError) as error: client.get('/healthz')
            self.assertEqual(error.exception.code, 'ACCESS_DENIED')
            self.assertEqual(call.call_count, 1)
        with patch('urllib.request.urlopen', side_effect=HTTPError('u',503,'Unavailable',{},None)) as call:
            with patch('time.sleep'):
                with self.assertRaises(APIError) as error: client.get('/healthz')
            self.assertEqual(error.exception.code, 'HTTP_503')
            self.assertEqual(call.call_count, 3)

    def test_conflicting_totals_fail(self):
        client = APIClient('https://example.invalid')
        responses = iter([{'dataset_version':'v1','items':[{}], 'limit':1,'offset':0,'total':2},
                          {'dataset_version':'v1','items':[{}], 'limit':1,'offset':1,'total':3}])
        client.get = lambda *a, **k: next(responses)
        with self.assertRaises(APIError): list(client.pages('/x',limit=1))

    def test_failure_preserves_existing_output(self):
        from rag_amazon.__main__ import build_artifacts
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)/'result'
            build_artifacts(snapshot(),base)
            before = (base/'snapshot.json').read_bytes()
            with self.assertRaises(ValueError): build_artifacts(snapshot(),base)
            self.assertEqual((base/'snapshot.json').read_bytes(),before)
            bad = snapshot()
            bad['products'] = []
            with self.assertRaises(ValueError): build_artifacts(bad,Path(tmp)/'bad')
            self.assertFalse((Path(tmp)/'bad').exists())
            self.assertFalse(list(Path(tmp).glob('.rag-build-*')))

class ReviewRegressionTests(unittest.TestCase):
    def test_untokenizable_review_is_reported_not_fatal(self):
        raw=snapshot()
        raw['reviews'][0]['record']['text']='!!! 👍'
        docs,report=preprocess(raw)
        self.assertEqual(len(docs),1)
        self.assertEqual(len(report['rejected']),1)
        self.assertEqual(BM25Index(docs).search('coffee')['status'],'ok')

    def test_search_output_cannot_overwrite_existing_file(self):
        from rag_amazon.__main__ import build_artifacts, main
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)/'result'
            build_artifacts(snapshot(),base)
            source=base/'snapshot.json'
            before=source.read_bytes()
            with patch('builtins.print'):
                code=main(['search','--index',str(base/'bm25_index.json'),'--query','coffee','--output',str(source)])
            self.assertEqual(code,1)
            self.assertEqual(source.read_bytes(),before)

    def test_index_schema_validates_all_handoff_fields(self):
        docs,_=preprocess(snapshot())
        for key,value in [('dataset_version',None),('dataset_version',17),('title',{}),('brand',[]),('price',False)]:
            invalid=json.loads(json.dumps(docs))
            invalid[0][key]=value
            with self.subTest(key=key,value=value):
                with self.assertRaises(ValueError): BM25Index(invalid)
        docs[0].pop('dataset_version')
        with self.assertRaises(ValueError): BM25Index(docs)

    def test_snapshot_url_must_be_safe_string(self):
        for value in (None,17,'https://user:password@example.invalid','https://example.invalid?secret=1'):
            raw=snapshot()
            raw['base_url']=value
            with self.subTest(value=value):
                with self.assertRaises(ValueError): preprocess(raw)

    def test_api_rejects_nan_and_repeated_keys(self):
        from unittest.mock import patch
        from io import BytesIO
        class Response(BytesIO):
            def geturl(self): return 'https://example.invalid/healthz'
        for data in (b'{"status":NaN}', b'{"status":"ok","status":"other"}'):
            with patch('urllib.request.urlopen',return_value=Response(data)):
                with self.assertRaises(APIError): APIClient('https://example.invalid').get('/healthz')

if __name__ == '__main__': unittest.main()
