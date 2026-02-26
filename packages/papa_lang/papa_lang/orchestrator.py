"""Orchestrator client — calls papa-app /orchestrate API."""

import httpx
from typing import Optional
from .types import OrchestrateResult


class Orchestrator:
    """Client for papa-app orchestrate endpoint. Uses papa-guard for input validation."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        *,
        route: str = "orchestrator",
        fallback: str = "single",
        module: str = "",
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.route = route
        self.fallback = fallback
        self.module = module

    async def orchestrate(
        self,
        query: str,
        session_id: Optional[str] = None,
        skip_validation: bool = False,
        force_single: bool = False,
    ) -> OrchestrateResult:
        """POST to /api/v1/ai/orchestrate. Returns response, hrs, verdict."""
        from papa_guard import Guard

        guard = Guard()
        guard_result = guard.check_input(query)
        if guard_result.blocked:
            return {
                "response": "",
                "agent_used": "guard",
                "hrs": 100.0,
                "verdict": "BLOCK",
                "flagged_claims": [guard_result.block_reason or "Input blocked"],
                "blocked": True,
                "retried": False,
                "swarm_mode": False,
                "rag_context_used": False,
                "mode": "orchestrate",
            }

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{self.base_url}/api/v1/ai/orchestrate",
                json={
                    "prompt": guard_result.sanitized_text,
                    "skip_validation": skip_validation,
                    "force_single": force_single,
                },
                headers=headers,
            )
            r.raise_for_status()
            return r.json()
