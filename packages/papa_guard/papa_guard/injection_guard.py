"""Injection guard — prompt injection detection (EN + RU)."""

import re
from .models import InjectionResult, InjectionSignal

INJECTION_PATTERNS = [
    (r"(?i)ignore\s+(all\s+)?previous\s+instructions", "HIGH"),
    (r"(?i)you\s+are\s+now\s+", "HIGH"),
    (r"(?i)system\s*:\s*", "HIGH"),
    (r"(?i)forget\s+(everything|all|your\s+instructions)", "HIGH"),
    (r"(?i)act\s+as\s+(if\s+you\s+are|a)\s+", "MEDIUM"),
    (r"(?i)do\s+not\s+follow\s+", "HIGH"),
    (r"(?i)override\s+(your\s+)?instructions", "HIGH"),
    (r"(?i)jailbreak", "HIGH"),
    (r"(?i)\bDAN\b", "HIGH"),
    (r"(?i)pretend\s+(you\s+are|to\s+be)", "MEDIUM"),
    (r"(?i)игнорируй\s+инструкции", "HIGH"),
    (r"(?i)забудь\s+всё", "HIGH"),
    (r"(?i)ты\s+теперь\s+", "HIGH"),
]


def check_injection(text: str, blocked_patterns: list[str] | None = None) -> InjectionResult:
    """Detect prompt injection patterns. Returns detected patterns and signals."""
    text = text or ""
    blocked_patterns = blocked_patterns or []
    detected: list[str] = []
    signals: list[InjectionSignal] = []

    for pattern, severity in INJECTION_PATTERNS:
        if re.search(pattern, text):
            detected.append(pattern)
            signals.append(InjectionSignal(pattern=pattern[:50], severity=severity))

    for bp in blocked_patterns:
        if bp.lower() in text.lower():
            detected.append(f"blocked:{bp}")
            signals.append(InjectionSignal(pattern=f"blocked:{bp}", severity="HIGH"))

    return InjectionResult(
        detected=len(detected) > 0,
        patterns=detected,
        count=len(detected),
        signals=signals,
    )
