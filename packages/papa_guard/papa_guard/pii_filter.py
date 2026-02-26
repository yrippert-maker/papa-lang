"""PII filter — ФЗ-152 compliant, Russian + international patterns."""

import re
from .models import PIIMatch, PIIResult

PII_PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone_ru": r"\b(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b",
    "phone_intl": r"\b\+?\d{1,3}[\s\-]?\(?\d{2,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{2,4}\b",
    "inn": r"\b\d{10}\b|\b\d{12}\b",
    "card_number": r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b",
    "passport_ru": r"\b\d{2}\s?\d{2}\s?\d{6}\b",
    "snils": r"\b\d{3}[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{2}\b",
    # Russian full name pattern (simplified: 2-3 words, Cyrillic)
    "full_name_ru": r"\b[А-ЯЁа-яё]{2,}\s+[А-ЯЁа-яё]{2,}(?:\s+[А-ЯЁа-яё]{2,})?\b",
}

REPLACEMENTS = {
    "email": "[EMAIL]",
    "phone_ru": "[ТЕЛЕФОН]",
    "phone_intl": "[PHONE]",
    "inn": "[ИНН]",
    "card_number": "[CARD]",
    "passport_ru": "[ПАСПОРТ]",
    "snils": "[СНИЛС]",
    "full_name_ru": "[ФИО]",
}


def check_pii(text: str) -> PIIResult:
    """Detect PII in text. Returns matches and sanitized text."""
    text = text or ""
    matches: list[tuple[str, int, int, str]] = []  # (type, start, end, full_match)

    for pii_type, pattern in PII_PATTERNS.items():
        for m in re.finditer(pattern, text):
            matches.append((pii_type, m.start(), m.end(), m.group()))

    pii_matches = [
        PIIMatch(type=t, value=full[:4] + "***", position=start)
        for t, start, _, full in matches
    ]

    # Build sanitized: replace from end to start to preserve indices
    sanitized = text
    for pii_type, start, end, _ in sorted(matches, key=lambda x: x[1], reverse=True):
        replacement = REPLACEMENTS.get(pii_type, "[PII]")
        sanitized = sanitized[:start] + replacement + sanitized[end:]

    return PIIResult(
        found=len(pii_matches) > 0,
        matches=pii_matches,
        count=len(pii_matches),
        sanitized_text=sanitized if pii_matches else text,
    )
