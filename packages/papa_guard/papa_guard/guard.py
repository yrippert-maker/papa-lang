"""Guard facade — PII + injection + cost in one call."""

from .models import GuardResult
from .pii_filter import check_pii
from .injection_guard import check_injection
from .cost_tracker import CostTracker


class Guard:
    """AI safety middleware: PII filter (ФЗ-152) + injection guard + cost tracker."""

    def __init__(
        self,
        pii_enabled: bool = True,
        injection_enabled: bool = True,
        cost_limit_usd: float = 100.0,
        blocked_patterns: list[str] | None = None,
    ):
        self.pii_enabled = pii_enabled
        self.injection_enabled = injection_enabled
        self.cost_tracker = CostTracker(cost_limit_usd=cost_limit_usd)
        self.blocked_patterns = blocked_patterns or []

    def check_input(
        self,
        text: str,
        model: str = "claude-sonnet",
        tokens: int | None = None,
    ) -> GuardResult:
        """
        Run PII, injection, and (optionally) cost checks.
        Returns sanitized text and block status.
        """
        text = text or ""
        tokens = tokens or max(100, len(text) // 4)

        # 1. PII check
        pii_result = check_pii(text)
        sanitized = pii_result.sanitized_text if pii_result.found else text

        if self.pii_enabled and pii_result.found:
            return GuardResult(
                sanitized_text=sanitized,
                pii_redacted_count=pii_result.count,
                blocked=True,
                block_reason="PII detected",
                injection_detected=False,
                cost_allowed=True,
            )

        # 2. Injection check
        inj_result = check_injection(text, self.blocked_patterns)

        if self.injection_enabled and inj_result.detected:
            return GuardResult(
                sanitized_text=sanitized,
                pii_redacted_count=pii_result.count,
                blocked=True,
                block_reason="Prompt injection detected",
                injection_detected=True,
                cost_allowed=True,
            )

        # 3. Cost check
        cost_result = self.cost_tracker.check_cost(model, tokens)

        return GuardResult(
            sanitized_text=sanitized,
            pii_redacted_count=pii_result.count,
            blocked=False,
            injection_detected=inj_result.detected,
            cost_allowed=cost_result.allowed,
        )
