"""Blockchain anchor for papa-lang — EU AI Act compliance."""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AnchorRecord:
    """Immutable record of an AI decision — logged to blockchain."""

    agent_name: str
    query_hash: str
    response_hash: str
    hrs_score: float
    verdict: str
    guard_level: str
    model: str
    timestamp: float = field(default_factory=time.time)
    papa_version: str = "1.0.0"

    def to_dict(self) -> dict:
        return {
            "agent": self.agent_name,
            "query_hash": self.query_hash,
            "response_hash": self.response_hash,
            "hrs": self.hrs_score,
            "verdict": self.verdict,
            "guard": self.guard_level,
            "model": self.model,
            "ts": self.timestamp,
            "papa_v": self.papa_version,
        }

    @property
    def fingerprint(self) -> str:
        """Cryptographic fingerprint of this record."""
        raw = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()


class BlockchainAnchor:
    """Abstract anchor interface."""

    def submit(self, record: AnchorRecord) -> str:
        raise NotImplementedError

    def verify(self, fingerprint: str) -> bool:
        raise NotImplementedError


class InMemoryAnchor(BlockchainAnchor):
    """Zero-dependency anchor for testing and development."""

    def __init__(self) -> None:
        self._log: List[dict] = []

    def submit(self, record: AnchorRecord) -> str:
        entry = {**record.to_dict(), "fingerprint": record.fingerprint}
        self._log.append(entry)
        print(f"[papa-anchor] submitted fingerprint={record.fingerprint[:16]}...")
        return record.fingerprint

    def verify(self, fingerprint: str) -> bool:
        return any(e["fingerprint"] == fingerprint for e in self._log)

    def get_log(self) -> List[dict]:
        return list(self._log)


class HyperledgerAnchor(BlockchainAnchor):
    """Hyperledger Fabric anchor via REST Gateway."""

    def __init__(
        self,
        gateway_url: str,
        channel: str = "papa-channel",
        chaincode: str = "papa-chaincode",
    ):
        self.gateway_url = gateway_url
        self.channel = channel
        self.chaincode = chaincode

    def submit(self, record: AnchorRecord) -> str:
        import urllib.request

        payload = json.dumps(
            {
                "channelId": self.channel,
                "chaincodeName": self.chaincode,
                "fcn": "SubmitRecord",
                "args": [json.dumps(record.to_dict())],
            }
        ).encode()
        req = urllib.request.Request(
            f"{self.gateway_url}/transactions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
            return result.get("transactionId", record.fingerprint)

    def verify(self, fingerprint: str) -> bool:
        import urllib.request

        url = f"{self.gateway_url}/transactions/{fingerprint}"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False


def get_anchor(mode: str, **kwargs) -> Optional[BlockchainAnchor]:
    if mode == "blockchain":
        gateway_url = kwargs.get("gateway_url")
        if gateway_url:
            return HyperledgerAnchor(gateway_url=gateway_url)
        return InMemoryAnchor()
    return None


def make_record(
    agent_name: str,
    query: str,
    response: str,
    hrs: float,
    verdict: str,
    guard: str,
    model: str,
) -> AnchorRecord:
    return AnchorRecord(
        agent_name=agent_name,
        query_hash=hashlib.sha256(query.encode()).hexdigest(),
        response_hash=hashlib.sha256(response.encode()).hexdigest(),
        hrs_score=hrs,
        verdict=verdict,
        guard_level=guard,
        model=model,
    )
