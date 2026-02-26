"""Swarm agents and consensus config for papa-lang compiler output."""

from dataclasses import dataclass
from typing import List, Optional, Any


@dataclass
class ConsensusConfig:
    required: int
    of: int


@dataclass
class SwarmAgent:
    """Agent config for swarm composition. Used by compiler-generated code."""

    name: str
    model: str = "claude-3-sonnet"
    guard: Any = None
    hrs_config: Any = None
    memory_enabled: bool = False


@dataclass
class SwarmRunner:
    """Swarm execution config. Used by compiler-generated code."""

    name: str
    agents: List[SwarmAgent]
    consensus: Optional[ConsensusConfig] = None
    anchor: str = "none"
    pii_filter: bool = False
    hrs_max: float = 0.30
