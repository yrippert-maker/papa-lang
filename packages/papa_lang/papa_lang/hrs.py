"""HRS (Hallucination Risk Score) monitor interface."""

from typing import Literal
from .types import HRSVerdict

Verdict = Literal["PASS", "WARN", "BLOCK"]


class HRSMonitor:
    """Interface for logging HRS verdicts. No-op by default; override for analytics."""

    def log_verdict(
        self,
        endpoint: str,
        hrs_score: float,
        decision: str,
        agent_used: str = "",
        query_category: str = "",
        was_retried: bool = False,
        retry_decision: str | None = None,
        latency_ms: int = 0,
        rag_context_used: bool = False,
    ) -> None:
        """Log HRS validation result. Override in subclass for persistence."""
        pass

    def get_summary(self) -> dict:
        """Return summary stats. Override for persistence."""
        return {}


def make_hrs_verdict(hrs: float, verdict: Verdict, flagged_claims: list[str] | None = None) -> dict:
    """Construct HRS verdict dict."""
    return {
        "hrs": hrs,
        "verdict": verdict,
        "flagged_claims": flagged_claims or [],
    }
