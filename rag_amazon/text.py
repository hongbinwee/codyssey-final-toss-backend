"""전처리/색인/질문에 같은 단어 분리 규칙을 적용한다."""
import re
import unicodedata

TOKENIZER_VERSION = 'unicode-word-v1'
STOPWORDS = frozenset('a an the is are was were it its this that of to for and or in on with as at by from be i my we our you your but'.split())


def tokenize(text):
    if not isinstance(text, str): raise ValueError('본문/질문은 문자열이어야 합니다.')
    tokens = re.findall(r'[^\W_]+', unicodedata.normalize('NFKC', text).casefold(), flags=re.UNICODE)
    return [word for word in tokens if word not in STOPWORDS]
