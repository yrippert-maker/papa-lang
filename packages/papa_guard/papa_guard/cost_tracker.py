"""Cost tracker — model pricing, daily budget soft/hard limits."""

from .models import CostCheckResult

MODEL_PRICING_PER_1K = {
    "claude-opus": 0.075,
    "claude-sonnet": 0.015,
    "claude-haiku": 0.003,
    "claude-sonnet-4-20250514": 0.015,
    "gpt-4": 0.06,
    "gpt-4o": 0.01,
    "gpt-3.5": 0.002,
    "gemini-pro": 0.00125,
    "gemini-flash": 0.000375,
}


class CostTracker:
    """Track AI API cost against budget limits."""

    def __init__(
        self,
        cost_limit_usd: float = 100.0,
        cost_spent_usd: float = 0.0,
    ):
        self.cost_limit_usd = cost_limit_usd
        self.cost_spent_usd = cost_spent_usd

    def check_cost(
        self,
        model: str = "claude-sonnet",
        tokens: int = 1000,
    ) -> CostCheckResult:
        """Check if cost is within budget. If allowed, increments spent."""
        price_per_1k = MODEL_PRICING_PER_1K.get(model, 0.015)
        cost = (tokens / 1000) * price_per_1k

        allowed = (self.cost_spent_usd + cost) <= self.cost_limit_usd
        if allowed:
            self.cost_spent_usd += cost

        remaining = self.cost_limit_usd - self.cost_spent_usd
        return CostCheckResult(
            allowed=allowed,
            cost_usd=round(cost, 6),
            remaining_usd=round(max(0, remaining), 4),
        )

    def reset(self) -> None:
        """Reset spent to zero."""
        self.cost_spent_usd = 0.0
