"""Conservative, offset-preserving redaction for explicit personal data."""

from __future__ import annotations

import re
from collections.abc import MutableMapping


_EMAIL = re.compile(
    r"(?<![A-Za-z0-9.!#$%&'*+/=?^_`{|}~-])"
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+"
    r"(?![A-Za-z0-9_-])"
)
_SSN = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
_PHONE = re.compile(
    r"(?<!\d)(?:\+?1[\s.-]?)?"
    r"(?:\(\s*\d{3}\s*\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)"
)
_EXPLICIT_CONTACT = re.compile(
    r"\b(?:call|text|contact|reach)\s+(?:me|us)\b"
    r"|\b(?:(?:my|our)\s+)?(?:phone|cell|mobile)\s+(?:number|#)\b"
    r"|\b(?:tel|telephone|fax)\s*[:#]",
    re.IGNORECASE,
)
_CONTACT_CONTEXT_CHARS = 60


def redact_explicit_pii(
    text: str, counts: MutableMapping[str, int] | None = None
) -> str:
    """Mask explicit PII without changing string length or whitespace offsets.

    Email and SSN patterns are explicit by shape. A phone-shaped string is only
    masked when a strong contact label occurs within 60 characters.
    """
    if not isinstance(text, str) or not text:
        return text

    candidates: list[tuple[int, int, str]] = []
    candidates.extend((match.start(), match.end(), "email") for match in _EMAIL.finditer(text))
    candidates.extend((match.start(), match.end(), "ssn") for match in _SSN.finditer(text))
    for match in _PHONE.finditer(text):
        start, end = match.span()
        prefix = text[max(0, start - _CONTACT_CONTEXT_CHARS):start]
        explicit_prefix = any(
            not re.search(r"\d", prefix[contact.end():])
            for contact in _EXPLICIT_CONTACT.finditer(prefix)
        )
        if explicit_prefix:
            candidates.append((start, end, "phone"))

    if not candidates:
        return text

    characters = list(text)
    masked_until = -1
    for start, end, kind in sorted(candidates):
        if start < masked_until:
            continue
        for index in range(start, end):
            if not characters[index].isspace():
                characters[index] = "█"
        masked_until = end
        if counts is not None:
            counts[kind] = counts.get(kind, 0) + 1
    return "".join(characters)
