"""AST nodes for .papa DSL."""

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class AgentDef:
    name: str
    model: str = "claude-3-sonnet"
    guard: str = "standard"  # strict | standard | minimal
    hrs_threshold: float = 0.15
    memory: bool = False
    line: int = 0


@dataclass
class ConsensusConfig:
    required: int
    of: int


@dataclass
class SwarmDef:
    name: str
    agents: List[str] = field(default_factory=list)
    consensus: Optional[ConsensusConfig] = None
    anchor: str = "none"
    pii: str = "none"
    hrs_max: float = 0.30
    line: int = 0


@dataclass
class PipelineDef:
    name: str
    route: str = "orchestrator"
    fallback: str = "single"
    module: str = ""
    line: int = 0


@dataclass
class Program:
    agents: List[AgentDef] = field(default_factory=list)
    swarms: List[SwarmDef] = field(default_factory=list)
    pipelines: List[PipelineDef] = field(default_factory=list)
    source_file: str = ""
