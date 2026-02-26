"""papa-lang — The AI-native language: swarm agents + HRS anti-hallucination."""

from .orchestrator import Orchestrator
from .hrs import HRSMonitor, make_hrs_verdict
from .types import OrchestrateResult, SwarmResult, HRSVerdict

__version__ = "0.1.0"
__all__ = [
    "Orchestrator",
    "HRSMonitor",
    "make_hrs_verdict",
    "HRSVerdict",
    "OrchestrateResult",
    "SwarmResult",
]
