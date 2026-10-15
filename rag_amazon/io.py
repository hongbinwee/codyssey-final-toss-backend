"""JSON 읽기/원자적 저장. 입력 자료와 원본 파일은 수정하지 않는다."""
import hashlib
import json
import os
import tempfile
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def decode_json(data):
    def invalid(value):
        raise ValueError('JSON에 유효하지 않은 숫자가 있습니다: ' + value)
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError('JSON의 중복 key: ' + key)
            result[key] = value
        return result
    return json.loads(data, parse_constant=invalid, object_pairs_hook=unique)


def read_json(path):
    return decode_json(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    path = Path(path)
    encoded = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        # 원자적으로 새 파일만 생성한다. 기존 원본/산출물은 덮어쓰지 않는다.
        os.link(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
