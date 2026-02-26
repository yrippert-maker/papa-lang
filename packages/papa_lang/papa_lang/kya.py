"""KYA (Know Your Agent) artifact generator for papa-lang."""

import hashlib
import json
import time
from pathlib import Path
from typing import Any

KYA_VERSION = "1.0"


def _iso(ts: float) -> str:
    import datetime

    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def generate_kya(
    agent: Any,
    source: str,
    issued_by: str = "Unknown",
    ttl_days: int = 365,
) -> dict:
    """Generate a KYA artifact dict from an AgentDef."""
    source_hash = hashlib.sha256(source.encode()).hexdigest()
    now = time.time()
    return {
        "kya_version": KYA_VERSION,
        "agent_id": f"urn:papa-lang:agent:{agent.name}",
        "issued_by": issued_by,
        "issued_at": _iso(now),
        "expires_at": _iso(now + ttl_days * 86400),
        "model": agent.model,
        "constraints": {
            "guard": agent.guard,
            "hrs_threshold": agent.hrs_threshold,
            "hrs_engine": getattr(agent, "hrs_engine", "default"),
            "memory": agent.memory,
            "retrieval": getattr(agent, "retrieval", "default"),
            "pii": "none",
            "anchor": "none",
            "observability": getattr(agent, "observability", "none"),
        },
        "source_hash": f"sha256:{source_hash}",
        "papa_lang_version": "1.0.0",
    }


def export_kya(kya: dict, output_path: Path) -> Path:
    """Write .kya.json file."""
    output_path = Path(output_path)
    path = output_path.with_suffix(".kya.json")
    path.write_text(json.dumps(kya, indent=2))
    return path


def verify_kya(kya_path: Path, source_path: Path) -> bool:
    """Verify that .kya.json matches the source .papa file."""
    kya = json.loads(kya_path.read_text())
    source = source_path.read_text()
    expected_hash = "sha256:" + hashlib.sha256(source.encode()).hexdigest()
    return kya.get("source_hash") == expected_hash
