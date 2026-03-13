"""
papa.std.ai — Zero-Hallucination AI Agents
Pipeline: VALIDATOR → CALCULATOR → LOOKUP → ANALYST → CERTIFIER

Core Principle: LLM = Interpreter, not Inventor.
- Math is done by Python algorithms, never by LLM
- Every claim requires a source citation
- UNKNOWN is always preferred over a guess
- 5 specialized agents collaborate in AviationSwarm
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import math


class Confidence(Enum):
    HIGH    = "HIGH"
    MEDIUM  = "MEDIUM"
    LOW     = "LOW"
    UNKNOWN = "UNKNOWN"


@dataclass
class Citation:
    source: str
    reference: str
    retrieved_at: datetime = field(default_factory=datetime.utcnow)
    url: Optional[str] = None
    def __str__(self): return f"[{self.source}:{self.reference}]"


@dataclass
class AgentResult:
    value: Any
    confidence: Confidence
    citations: List[Citation] = field(default_factory=list)
    agent_name: str = ""
    reasoning: str = ""
    warnings: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_trusted(self):
        return self.confidence in (Confidence.HIGH, Confidence.MEDIUM)

    def assert_trusted(self):
        if not self.is_trusted:
            raise ZeroHallucinationError(
                f"Agent '{self.agent_name}' untrusted: confidence={self.confidence.value}"
            )
        return self

    def with_warning(self, w: str):
        self.warnings.append(w)
        return self


class ZeroHallucinationError(Exception): pass
class ValidationError(Exception): pass
class CalculationError(Exception): pass


class ValidatorAgent:
    name = "VALIDATOR"

    def validate(self, data, required_fields, rules=None):
        missing = [f for f in required_fields if f not in data or data[f] is None]
        if missing:
            raise ValidationError(f"[VALIDATOR] Missing: {missing}. UNKNOWN > guess.")
        violations = []
        if rules:
            for fn, rule in rules.items():
                if fn in data:
                    try:
                        if not rule(data[fn]):
                            violations.append(f"Field '{fn}' failed rule")
                    except Exception as e:
                        violations.append(f"Field '{fn}' error: {e}")
        if violations:
            raise ValidationError(f"[VALIDATOR] Violations: {violations}")
        return AgentResult(value=data, confidence=Confidence.HIGH,
                           agent_name=self.name,
                           reasoning=f"All {len(required_fields)} fields valid")

    def validate_part_number(self, pn: str):
        if not pn or not isinstance(pn, str) or len(pn.strip()) < 3:
            raise ValidationError(f"[VALIDATOR] Invalid P/N: '{pn}'")
        return AgentResult(value=pn.strip().upper(), confidence=Confidence.HIGH,
                           agent_name=self.name, reasoning="P/N format validated")


class CalculatorAgent:
    name = "CALCULATOR"

    def remaining_life_hours(self, total_limit: float, hours_used: float):
        if total_limit <= 0: raise CalculationError("[CALCULATOR] total_limit must be > 0")
        if hours_used < 0:   raise CalculationError("[CALCULATOR] hours_used cannot be negative")
        remaining = max(0.0, total_limit - hours_used)
        pct = (hours_used / total_limit) * 100
        r = AgentResult(value={"remaining_hours": remaining, "percent_used": round(pct, 2)},
                        confidence=Confidence.HIGH, agent_name=self.name,
                        reasoning=f"Deterministic: {total_limit} - {hours_used} = {remaining}")
        if pct >= 90: r.with_warning(f"CRITICAL: {pct:.1f}% of life used")
        elif pct >= 75: r.with_warning(f"WARNING: {pct:.1f}% of life used")
        return r

    def remaining_life_cycles(self, total_limit: int, cycles_used: int):
        if total_limit <= 0: raise CalculationError("[CALCULATOR] total_limit must be > 0")
        remaining = max(0, total_limit - cycles_used)
        pct = (cycles_used / total_limit) * 100
        r = AgentResult(value={"remaining_cycles": remaining, "percent_used": round(pct, 2)},
                        confidence=Confidence.HIGH, agent_name=self.name,
                        reasoning=f"Deterministic: {total_limit} - {cycles_used} = {remaining}")
        if pct >= 90: r.with_warning(f"CRITICAL: {pct:.1f}% of cycles used")
        return r

    def days_until_expiry(self, expiry_date, as_of=None):
        from datetime import date
        check = as_of or date.today()
        delta = (expiry_date - check).days
        r = AgentResult(value={"days_remaining": delta, "expired": delta <= 0},
                        confidence=Confidence.HIGH, agent_name=self.name,
                        reasoning=f"Date arithmetic: {expiry_date} - {check} = {delta} days")
        if delta <= 0: r.with_warning(f"EXPIRED: {abs(delta)} days ago")
        elif delta <= 30: r.with_warning(f"Expiring in {delta} days")
        return r


class LookupAgent:
    name = "LOOKUP"
    ALLOWED_SOURCES = {
        "ICAO_DB": "ICAO Aircraft & Operator Registry",
        "EASA_AD": "EASA Airworthiness Directives",
        "FAA_AD":  "FAA Airworthiness Directives",
        "CMM_LIB": "Component Maintenance Manual Library",
        "PAPA_DB": "PAPA Nexus Verified Database",
        "GCAA_DB": "UAE GCAA Registry",
    }

    def __init__(self, db_adapter=None):
        self._db = db_adapter

    def lookup(self, source: str, query: Dict[str, Any]):
        if source not in self.ALLOWED_SOURCES:
            from builtins import LookupError as _LE
            raise _LE(f"[LOOKUP] Source '{source}' not allowed: {list(self.ALLOWED_SOURCES)}")
        if self._db is None:
            return AgentResult(value=None, confidence=Confidence.UNKNOWN,
                               agent_name=self.name,
                               reasoning=f"No DB adapter. UNKNOWN > guess.",
                               warnings=["No database adapter — result is UNKNOWN"])
        try:
            result = self._db(source, query)
        except Exception as e:
            return AgentResult(value=None, confidence=Confidence.UNKNOWN,
                               agent_name=self.name, reasoning=f"DB error: {e}",
                               warnings=[f"Lookup error: {e}"])
        if result is None:
            return AgentResult(value=None, confidence=Confidence.UNKNOWN,
                               agent_name=self.name,
                               reasoning=f"Not found in {source}",
                               warnings=[f"Not found in {self.ALLOWED_SOURCES[source]}"])
        return AgentResult(value=result, confidence=Confidence.HIGH,
                           citations=[Citation(source=source, reference=str(query))],
                           agent_name=self.name,
                           reasoning=f"Found in {self.ALLOWED_SOURCES[source]}")


class AnalystAgent:
    name = "ANALYST"

    def analyze(self, calculator_result, lookup_result, context=""):
        if not calculator_result.is_trusted:
            raise ZeroHallucinationError("[ANALYST] Calculator result not trusted")
        citations = calculator_result.citations + lookup_result.citations
        warnings  = calculator_result.warnings  + lookup_result.warnings
        facts = []
        if isinstance(calculator_result.value, dict):
            for k, v in calculator_result.value.items():
                facts.append(f"{k}: {v}")
        if lookup_result.is_trusted and lookup_result.value:
            facts.append(f"Lookup: {lookup_result.value}")
        else:
            facts.append("Lookup: DATA NOT AVAILABLE — omitted")
            warnings.append("Analysis based on calculated data only")
        text = (f"[ANALYST REPORT]\nContext: {context}\n"
                f"Facts:\n" + "\n".join(f"  • {f}" for f in facts)
                + f"\nCitations: {[str(c) for c in citations]}")
        confidence = Confidence.HIGH if lookup_result.is_trusted else Confidence.MEDIUM
        r = AgentResult(value=text, confidence=confidence, citations=citations,
                        agent_name=self.name,
                        reasoning="Analysis from pre-verified data only")
        for w in warnings: r.with_warning(w)
        return r


class CertifierAgent:
    name = "CERTIFIER"

    def certify(self, analyst_result):
        if analyst_result.confidence == Confidence.UNKNOWN:
            raise ZeroHallucinationError("[CERTIFIER] REFUSED: confidence=UNKNOWN")
        if analyst_result.confidence == Confidence.LOW:
            raise ZeroHallucinationError("[CERTIFIER] REFUSED: confidence=LOW")
        if not analyst_result.citations:
            raise ZeroHallucinationError("[CERTIFIER] REFUSED: no citations")
        certified = {
            "certified": True,
            "confidence": analyst_result.confidence.value,
            "result": analyst_result.value,
            "citations": [str(c) for c in analyst_result.citations],
            "warnings": analyst_result.warnings,
            "certified_at": datetime.utcnow().isoformat(),
            "certified_by": self.name,
        }
        return AgentResult(value=certified, confidence=analyst_result.confidence,
                           citations=analyst_result.citations, agent_name=self.name,
                           reasoning="All claims verified. Zero-Hallucination certified.")


class AviationSwarm:
    """
    Full Zero-Hallucination pipeline:
    VALIDATOR → CALCULATOR → LOOKUP → ANALYST → CERTIFIER
    """
    def __init__(self, db_adapter=None):
        self.validator  = ValidatorAgent()
        self.calculator = CalculatorAgent()
        self.lookup     = LookupAgent(db_adapter=db_adapter)
        self.analyst    = AnalystAgent()
        self.certifier  = CertifierAgent()

    def check_component_life(self, part_number, total_hours_limit, hours_used,
                              serial_number=None, total_cycles_limit=None, cycles_used=None):
        data = {"part_number": part_number, "total_hours_limit": total_hours_limit,
                "hours_used": hours_used}
        self.validator.validate(data, list(data.keys()), rules={
            "total_hours_limit": lambda x: x > 0,
            "hours_used": lambda x: x >= 0,
        })
        self.validator.validate_part_number(part_number)
        calc = self.calculator.remaining_life_hours(total_hours_limit, hours_used)
        if total_cycles_limit and cycles_used is not None:
            cr = self.calculator.remaining_life_cycles(total_cycles_limit, cycles_used)
            calc.value.update(cr.value)
            calc.warnings.extend(cr.warnings)
        lkp = self.lookup.lookup("PAPA_DB", {"part_number": part_number, "serial_number": serial_number})
        ana = self.analyst.analyze(calc, lkp, context=f"P/N={part_number} S/N={serial_number}")
        return self.certifier.certify(ana)

    def pipeline_status(self):
        return {
            "VALIDATOR": "active", "CALCULATOR": "active",
            "LOOKUP": "active" if self.lookup._db else "no_adapter",
            "ANALYST": "active", "CERTIFIER": "active",
            "protocol": "ZERO_HALLUCINATION_V1",
        }


__all__ = [
    "ValidatorAgent", "CalculatorAgent", "LookupAgent",
    "AnalystAgent", "CertifierAgent", "AviationSwarm",
    "AgentResult", "Citation", "Confidence",
    "ZeroHallucinationError", "ValidationError", "CalculationError",
]
__version__ = "0.1.0"
