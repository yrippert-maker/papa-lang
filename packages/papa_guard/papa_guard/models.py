"""Pydantic models for papa-guard."""

from pydantic import BaseModel
from typing import List, Optional


class PIIMatch(BaseModel):
    type: str
    value: str
    position: int


class PIIResult(BaseModel):
    found: bool
    matches: List[PIIMatch]
    count: int
    sanitized_text: str = ""


class InjectionSignal(BaseModel):
    pattern: str
    severity: str = "MEDIUM"  # HIGH | MEDIUM


class InjectionResult(BaseModel):
    detected: bool
    patterns: List[str]
    count: int
    signals: List[InjectionSignal] = []


class CostCheckResult(BaseModel):
    allowed: bool
    cost_usd: float
    remaining_usd: float


class GuardResult(BaseModel):
    sanitized_text: str
    pii_redacted_count: int = 0
    blocked: bool = False
    block_reason: Optional[str] = None
    injection_detected: bool = False
    cost_allowed: bool = True
