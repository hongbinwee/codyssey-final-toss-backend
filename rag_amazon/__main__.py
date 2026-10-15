"""python -m rag_amazon 으로 실행."""
import argparse
import json
import shutil
import tempfile
import time
from pathlib import Path

from .client import APIClient, APIError, CATEGORIES, DEFAULT_URL
from .io import digest, read_json, write_json
from .preprocess import preprocess, verify_documents


def build_artifacts(raw, output_dir, mappings=None):
    from .index import BM25Index
    output_dir = Path(output_dir)
    if output_dir.exists(): raise ValueError('출력 폴더가 이미 있습니다. 새 폴더를 지정하세요.')
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.rag-build-', dir=str(output_dir.parent)))
    try:
        started = time.perf_counter()
        documents, report = preprocess(raw, mappings)
        index = BM25Index(documents)
        write_json(staging/'snapshot.json', raw)
        write_json(staging/'processed_documents.json', documents)
        write_json(staging/'corpus.json', [d['text'] for d in documents])
        write_json(staging/'tokenized_corpus.json', index.tokens)
        write_json(staging/'preprocess_report.json', report)
        if mappings is not None: write_json(staging/'commerce_mapping.json', mappings)
        index.save(staging/'bm25_index.json')
        loaded = BM25Index.load(staging/'bm25_index.json')
        if loaded.documents != documents: raise ValueError('색인 roundtrip에서 문서가 달라졌습니다.')
        verified = verify_documents(raw, documents, mappings)
        write_json(staging/'verification.json', {**verified, 'index_roundtrip': True,
                                                'source_kind': raw['source_kind']})
        write_json(staging/'manifest.json', {'schema_version': 'rag-build-v1',
                  'dataset_version': raw['dataset_version'], 'source_kind': raw['source_kind'],
                  'document_count': len(documents), 'snapshot_sha256': digest(raw),
                  'documents_sha256': digest(documents), 'build_seconds': time.perf_counter() - started,
                  'commerce_mapping_complete': report['commerce_mapping_missing'] == 0})
        staging.rename(output_dir)
    finally:
        if staging.exists(): shutil.rmtree(staging)
    return {'status': 'ok', 'output_dir': str(output_dir), **report}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Amazon 샘플 전처리·BM25 색인 및 handoff 검증')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('fetch', 'run'):
        p = commands.add_parser(name)
        p.add_argument('--base-url', default=DEFAULT_URL)
        p.add_argument('--category', action='append', choices=CATEGORIES)
        p.add_argument('--products-per-category', type=int, default=10)
        p.add_argument('--timeout', type=float, default=20)
        if name == 'fetch': p.add_argument('--output', type=Path, required=True)
        else:
            p.add_argument('--output-dir', type=Path, required=True)
            p.add_argument('--mapping', type=Path)
    p = commands.add_parser('build')
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--mapping', type=Path)
    p = commands.add_parser('search')
    p.add_argument('--index', type=Path, required=True)
    p.add_argument('--query', required=True)
    p.add_argument('--top-k', type=int, default=5)
    p.add_argument('--document-type', choices=('product', 'review'))
    p.add_argument('--category', choices=CATEGORIES)
    p.add_argument('--product-id')
    p.add_argument('--min-query-coverage', type=float, default=0.5)
    p.add_argument('--output', type=Path)
    p = commands.add_parser('verify')
    p.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command in ('fetch', 'run'):
            destination = args.output if args.command == 'fetch' else args.output_dir
            if destination.exists(): raise ValueError('출력 경로가 이미 있습니다. 새 경로를 지정하세요.')
            raw = APIClient(args.base_url, timeout=args.timeout).snapshot(
                args.category or CATEGORIES, args.products_per_category)
            if args.command == 'fetch':
                write_json(args.output, raw)
                result = {'status': 'ok', 'products': len(raw['products']), 'reviews': len(raw['reviews']),
                          'dataset_version': raw['dataset_version'], 'output': str(args.output)}
            else:
                mapping = read_json(args.mapping) if args.mapping else None
                result = build_artifacts(raw, args.output_dir, mapping)
        elif args.command == 'build':
            result = build_artifacts(read_json(args.input), args.output_dir,
                                     read_json(args.mapping) if args.mapping else None)
        elif args.command == 'search':
            from .index import BM25Index
            if args.output and args.output.exists():
                raise ValueError('검색 출력 경로가 이미 있습니다. 새 경로를 지정하세요.')
            index = BM25Index.load(args.index)
            result = index.search(args.query, args.top_k, args.document_type, args.category,
                                  args.product_id, args.min_query_coverage)
            if args.output: write_json(args.output, result)
        else:
            from .index import BM25Index
            base = args.output_dir
            mapping = read_json(base/'commerce_mapping.json') if (base/'commerce_mapping.json').exists() else None
            raw, documents = read_json(base/'snapshot.json'), read_json(base/'processed_documents.json')
            result = verify_documents(raw, documents, mapping)
            if read_json(base/'corpus.json') != [d['text'] for d in documents]:
                raise ValueError('corpus와 documents 순서/본문이 다릅니다.')
            index = BM25Index.load(base/'bm25_index.json')
            if index.documents != documents or index.tokens != read_json(base/'tokenized_corpus.json'):
                raise ValueError('index와 documents/tokens가 다릅니다.')
            manifest = read_json(base/'manifest.json')
            if manifest.get('snapshot_sha256') != digest(raw) or manifest.get('documents_sha256') != digest(documents):
                raise ValueError('manifest hash가 다릅니다.')
            result['index_roundtrip'] = True
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, APIError, ImportError) as exc:
        if isinstance(exc, APIError): code = exc.code
        elif isinstance(exc, ImportError): code = 'DEPENDENCY_MISSING'
        elif isinstance(exc, OSError): code = 'FILE_ERROR'
        else: code = 'INVALID_DATA'
        result = {'schema_version': 'rag-result-v1', 'status': 'error', 'results': [],
                  'error': {'code': code, 'message': str(exc)}}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1


if __name__ == '__main__': raise SystemExit(main())
