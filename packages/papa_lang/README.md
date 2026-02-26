# papa-lang

> The AI-native language: swarm agents + HRS anti-hallucination.

## Install

```bash
pip install papa-lang
```

Requires `papa-guard` (installed automatically).

## Quick Start

```python
import asyncio
from papa_lang import Orchestrator

async def main():
    orch = Orchestrator(base_url="http://localhost:8000", api_key="your-token")
    result = await orch.orchestrate("What is the capital of France?")
    print(result["response"])
    print(f"HRS: {result['hrs']}% — {result['verdict']}")

asyncio.run(main())
```

## Exports

- `Orchestrator` — client for papa-app /orchestrate
- `HRSMonitor` — verdict logging interface
- `HRSVerdict`, `OrchestrateResult`, `SwarmResult` — types
