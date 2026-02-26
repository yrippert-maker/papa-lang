"""Types for papa-lang ecosystem."""

from typing import TypedDict, Literal, Optional


class HRSVerdict(TypedDict, total=False):
    hrs: float
    verdict: Literal["PASS", "WARN", "BLOCK"]
    flagged_claims: list[str]


class OrchestrateResult(TypedDict, total=False):
    response: str
    agent_used: str
    hrs: float
    verdict: str
    flagged_claims: list[str]
    blocked: bool
    retried: bool
    swarm_mode: bool
    rag_context_used: bool
    mode: str


class SwarmResult(TypedDict, total=False):
    response: str
    consensus_score: float
    agents_used: int
    hrs: float
    verdict: str
