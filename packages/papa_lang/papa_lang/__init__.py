"""papa-lang — The AI-native language: swarm agents + HRS anti-hallucination."""

from .orchestrator import Orchestrator
from .hrs import HRSConfig, HRSMonitor, make_hrs_verdict
from .swarm import SwarmAgent, SwarmRunner, ConsensusConfig
from .types import OrchestrateResult, SwarmResult, HRSVerdict

__version__ = "0.2.0"
__all__ = [
    "Orchestrator",
    "HRSMonitor",
    "make_hrs_verdict",
    "HRSVerdict",
    "OrchestrateResult",
    "SwarmResult",
    "HRSConfig",
    "SwarmAgent",
    "SwarmRunner",
    "ConsensusConfig",
]
