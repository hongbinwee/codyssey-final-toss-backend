"""고정 샘플의 연결 검증. 전체 검색 품질 평가와 구분한다."""
import argparse
import time
from pathlib import Path

from .index import BM25Index
from .io import read_json, write_json
from .preprocess import verify_documents


def run_cases(base, cases):
    base = Path(base)
    raw, documents = read_json(base/'snapshot.json'), read_json(base/'processed_documents.json')
    mapping = read_json(base/'commerce_mapping.json') if (base/'commerce_mapping.json').exists() else None
    verified = verify_documents(raw, documents, mapping)
    index = BM25Index.load(base/'bm25_index.json')
    if index.documents != documents: raise ValueError('색인과 검증 문서가 다릅니다.')
    by_id = {d['document_id']: d for d in documents}
    results = []
    for case in cases:
        started = time.perf_counter()
        try:
            response = index.search(case['query'], top_k=5,
                                    category=case.get('category'), document_type=case.get('document_type'))
        except ValueError as error:
            response = {'status': 'error', 'results': [], 'error': {'code':'INVALID_QUERY','message':str(error)}}
        evidence_ok = all(all(hit[k] == by_id[hit['document_id']][k] for k in
                              ('product_id','source_id','text','source_hash','dataset_version'))
                          for hit in response['results'])
        status_ok = response['status'] == case['expected_status']
        product_ok = not case.get('expected_product_id') or any(
            hit['product_id'] == case['expected_product_id'] for hit in response['results'])
        results.append({'case':case, 'passed': evidence_ok and status_ok and product_ok,
                        'elapsed_ms': (time.perf_counter()-started)*1000,
                        'original_evidence_verified': evidence_ok, 'response':response})
    return {'status':'ok' if all(r['passed'] for r in results) else 'failed',
            'source_kind': raw['source_kind'], 'dataset_version': raw['dataset_version'],
            'verified_documents': verified['verified_documents'],
            'passed':sum(r['passed'] for r in results), 'total':len(results), 'cases':results,
            'scope':'소규모 고정 샘플의 연결 smoke 검증; 일반 검색 정확도·한국어 품질 평가가 아님'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',type=Path,required=True)
    p.add_argument('--cases',type=Path,default=Path(__file__).parent/'tests/search_cases.json')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists(): p.error('출력 파일이 이미 있습니다. 새 경로를 지정하세요.')
    report=run_cases(args.data_dir,read_json(args.cases))
    write_json(args.output,report)
    print(f"smoke {report['passed']}/{report['total']}, status={report['status']}")
    return 0 if report['status']=='ok' else 1


if __name__=='__main__': raise SystemExit(main())
