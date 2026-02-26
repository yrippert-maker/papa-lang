"""PII filtering backends for papa-lang swarms — Presidio (v0.3)."""

import re
from typing import Optional


class PIIFilter:
    """Base PII filter interface."""

    def filter(self, text: str) -> str:
        raise NotImplementedError


class PresidioPIIFilter(PIIFilter):
    """Microsoft Presidio. pip install presidio-analyzer presidio-anonymizer"""

    def __init__(self, language: str = "en", score_threshold: float = 0.5):
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_anonymizer import AnonymizerEngine
        except ImportError:
            raise ImportError("Run: pip install papa-lang[presidio]") from None
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        self.language = language
        self.score_threshold = score_threshold

    def filter(self, text: str) -> str:
        results = self.analyzer.analyze(
            text=text,
            language=self.language,
            score_threshold=self.score_threshold,
        )
        return self.anonymizer.anonymize(text=text, analyzer_results=results).text


class MaskPIIFilter(PIIFilter):
    """Regex-based PII mask — zero deps."""

    PATTERNS = [
        (re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I), "[EMAIL]"),
        (re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"), "[PHONE]"),
    ]

    def filter(self, text: str) -> str:
        result = text
        for pattern, replacement in self.PATTERNS:
            result = pattern.sub(replacement, result)
        return result


def get_pii_filter(mode: str) -> Optional[PIIFilter]:
    if mode == "presidio":
        return PresidioPIIFilter()
    if mode in ("filter", "mask"):
        return MaskPIIFilter()
    return None
