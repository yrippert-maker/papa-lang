"""papa-guard — AI safety middleware for Russian-language AI systems."""

from .guard import Guard
from .models import GuardResult, PIIResult, InjectionResult, CostCheckResult

__version__ = "0.1.0"
__all__ = ["Guard", "GuardResult", "PIIResult", "InjectionResult", "CostCheckResult", "check_pii", "check_injection"]

from .pii_filter import check_pii
from .injection_guard import check_injection
