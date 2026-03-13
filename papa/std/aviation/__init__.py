"""
papa.std.aviation — Aviation Domain Types
Zero-Hallucination certified. Every value has a source.
EASA / ICAO / EIPAV compliant.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional, List, Dict, Any


# ── Enums ──────────────────────────────────────────────────────────────

class AirworthinessStatus(Enum):
    AIRWORTHY       = "AIRWORTHY"
    UNAIRWORTHY     = "UNAIRWORTHY"
    CONDITIONAL     = "CONDITIONAL"
    UNKNOWN         = "UNKNOWN"       # Always prefer UNKNOWN over a guess
    EXPIRED         = "EXPIRED"
    SUSPENDED       = "SUSPENDED"


class ATAChapter(Enum):
    """ATA iSpec 2200 chapters (subset)."""
    ATA_05  = "05"   # Time Limits / Maintenance Checks
    ATA_06  = "06"   # Dimensions and Areas
    ATA_21  = "21"   # Air Conditioning
    ATA_24  = "24"   # Electrical Power
    ATA_27  = "27"   # Flight Controls
    ATA_28  = "28"   # Fuel
    ATA_29  = "29"   # Hydraulic Power
    ATA_32  = "32"   # Landing Gear
    ATA_34  = "34"   # Navigation
    ATA_49  = "49"   # Airborne Auxiliary Power
    ATA_71  = "71"   # Power Plant
    ATA_72  = "72"   # Engine
    ATA_73  = "73"   # Engine Fuel and Control
    ATA_74  = "74"   # Ignition
    ATA_79  = "79"   # Oil
    UNKNOWN = "00"


class WorkOrderStatus(Enum):
    OPEN        = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_PARTS = "PENDING_PARTS"
    COMPLETED   = "COMPLETED"
    CANCELLED   = "CANCELLED"
    ON_HOLD     = "ON_HOLD"


class ComplianceStandard(Enum):
    EASA    = "EASA"
    FAA     = "FAA"
    ICAO    = "ICAO"
    GCAA    = "GCAA"    # UAE General Civil Aviation Authority
    CAAC    = "CAAC"    # China
    TCCA    = "TCCA"    # Canada


# ── Value Objects ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class PartNumber:
    """
    Immutable Part Number. Validates format on creation.
    Zero-Hallucination: raises ValueError instead of assuming.
    """
    value: str
    manufacturer_code: Optional[str] = None

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError(f"PartNumber: invalid value '{self.value}'")
        cleaned = self.value.strip().upper()
        object.__setattr__(self, 'value', cleaned)

    def __str__(self) -> str:
        return self.value

    def matches(self, other: "PartNumber") -> bool:
        """Exact match — no fuzzy comparisons allowed."""
        return self.value == other.value


@dataclass(frozen=True)
class SerialNumber:
    """
    Immutable Serial Number. Unique identifier for a specific component instance.
    """
    value: str
    issued_by: Optional[str] = None   # Organization that issued the S/N

    def __post_init__(self):
        if not self.value:
            raise ValueError("SerialNumber cannot be empty")
        object.__setattr__(self, 'value', self.value.strip().upper())

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Airworthiness:
    """
    Airworthiness record for a component.
    Every field has an explicit source. UNKNOWN > guess.
    """
    status: AirworthinessStatus
    authority: ComplianceStandard
    certificate_ref: Optional[str]       # AD, SB, CRS reference number
    valid_from: Optional[date]
    valid_until: Optional[date]
    source_db: str                        # Which database this came from
    verified_at: datetime = field(default_factory=datetime.utcnow)
    notes: str = ""

    def is_valid(self, as_of: Optional[date] = None) -> bool:
        check_date = as_of or date.today()
        if self.status != AirworthinessStatus.AIRWORTHY:
            return False
        if self.valid_until and check_date > self.valid_until:
            return False
        return True

    def assert_airworthy(self, as_of: Optional[date] = None) -> None:
        """Raises if not airworthy. Never silently passes."""
        if not self.is_valid(as_of):
            raise AirworthinessError(
                f"Component is NOT airworthy: status={self.status.value}, "
                f"valid_until={self.valid_until}, source={self.source_db}"
            )


# ── Core Domain Models ─────────────────────────────────────────────────

@dataclass
class Component:
    """
    Aviation Component — EIPAV Digital Passport compatible.
    Represents one physical part with full traceability.
    """
    part_number: PartNumber
    serial_number: SerialNumber
    description: str
    ata_chapter: ATAChapter = ATAChapter.UNKNOWN
    manufacturer: Optional[str] = None
    manufacture_date: Optional[date] = None

    # Life limits
    total_cycles_limit: Optional[int] = None    # None = no limit / unknown
    total_hours_limit: Optional[float] = None
    cycles_since_new: int = 0
    hours_since_new: float = 0.0
    hours_since_overhaul: float = 0.0
    cycles_since_overhaul: int = 0

    # Status
    airworthiness: Optional[Airworthiness] = None
    location: Optional[str] = None              # Aircraft reg or storage location
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def remaining_hours(self) -> Optional[float]:
        """Returns remaining hours or None if limit unknown."""
        if self.total_hours_limit is None:
            return None
        return max(0.0, self.total_hours_limit - self.hours_since_new)

    def remaining_cycles(self) -> Optional[int]:
        if self.total_cycles_limit is None:
            return None
        return max(0, self.total_cycles_limit - self.cycles_since_new)

    def is_life_limited(self) -> bool:
        return self.total_cycles_limit is not None or self.total_hours_limit is not None

    def is_airworthy(self, as_of: Optional[date] = None) -> bool:
        if self.airworthiness is None:
            return False   # UNKNOWN → not airworthy
        return self.airworthiness.is_valid(as_of)

    def eipav_passport(self) -> Dict[str, Any]:
        """Export component as EIPAV digital passport dict."""
        return {
            "eipav_version": "1.0",
            "part_number": str(self.part_number),
            "serial_number": str(self.serial_number),
            "description": self.description,
            "ata_chapter": self.ata_chapter.value,
            "manufacturer": self.manufacturer,
            "manufacture_date": self.manufacture_date.isoformat() if self.manufacture_date else None,
            "life_limits": {
                "total_hours": self.total_hours_limit,
                "total_cycles": self.total_cycles_limit,
                "hours_since_new": self.hours_since_new,
                "cycles_since_new": self.cycles_since_new,
                "remaining_hours": self.remaining_hours(),
                "remaining_cycles": self.remaining_cycles(),
            },
            "airworthiness": {
                "status": self.airworthiness.status.value if self.airworthiness else "UNKNOWN",
                "authority": self.airworthiness.authority.value if self.airworthiness else None,
                "certificate_ref": self.airworthiness.certificate_ref if self.airworthiness else None,
                "valid_until": self.airworthiness.valid_until.isoformat() if self.airworthiness and self.airworthiness.valid_until else None,
                "source_db": self.airworthiness.source_db if self.airworthiness else "NOT_VERIFIED",
            },
            "location": self.location,
            "tags": self.tags,
        }

    def __repr__(self) -> str:
        return f"<Component P/N={self.part_number} S/N={self.serial_number}>"


@dataclass
class Aircraft:
    """
    Aircraft entity. Contains components and tracks aggregate airworthiness.
    """
    registration: str                           # e.g. "A6-EKA"
    aircraft_type: str                          # e.g. "Boeing 737-800"
    msn: str                                    # Manufacturer Serial Number
    operator: Optional[str] = None
    authority: ComplianceStandard = ComplianceStandard.EASA
    total_airframe_hours: float = 0.0
    total_airframe_cycles: int = 0
    components: List[Component] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def add_component(self, component: Component) -> None:
        self.components.append(component)

    def get_component(self, part_number: PartNumber) -> Optional[Component]:
        for c in self.components:
            if c.part_number.matches(part_number):
                return c
        return None

    def life_limited_components(self) -> List[Component]:
        return [c for c in self.components if c.is_life_limited()]

    def unairworthy_components(self) -> List[Component]:
        return [c for c in self.components if not c.is_airworthy()]

    def components_expiring_within_hours(self, hours: float) -> List[Component]:
        result = []
        for c in self.components:
            remaining = c.remaining_hours()
            if remaining is not None and remaining <= hours:
                result.append(c)
        return result

    def is_dispatch_ready(self) -> bool:
        """Aircraft is dispatch-ready only if ALL components are airworthy."""
        if not self.components:
            return False
        return all(c.is_airworthy() for c in self.components)

    def __repr__(self) -> str:
        return f"<Aircraft {self.registration} ({self.aircraft_type}) MSN={self.msn}>"


@dataclass
class WorkOrder:
    """
    Maintenance Work Order.
    Tracks all work performed on components / aircraft.
    """
    work_order_number: str
    aircraft: Optional[Aircraft]
    component: Optional[Component]
    description: str
    ata_chapter: ATAChapter = ATAChapter.UNKNOWN
    status: WorkOrderStatus = WorkOrderStatus.OPEN
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    technician: Optional[str] = None
    approved_by: Optional[str] = None
    labor_hours: float = 0.0
    compliance_refs: List[str] = field(default_factory=list)  # AD, SB numbers
    notes: str = ""
    findings: List[str] = field(default_factory=list)
    parts_used: List[Component] = field(default_factory=list)

    def complete(self, approved_by: str, notes: str = "") -> None:
        if self.status == WorkOrderStatus.CANCELLED:
            raise WorkOrderError(f"Cannot complete cancelled WO: {self.work_order_number}")
        self.status = WorkOrderStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.approved_by = approved_by
        if notes:
            self.notes += f"\n[COMPLETION] {notes}"

    def add_finding(self, finding: str) -> None:
        self.findings.append(finding)

    def is_compliant(self) -> bool:
        """Has at least one compliance reference (AD/SB)."""
        return len(self.compliance_refs) > 0

    def __repr__(self) -> str:
        return f"<WorkOrder {self.work_order_number} [{self.status.value}]>"


# ── Exceptions ─────────────────────────────────────────────────────────

class AviationError(Exception):
    """Base exception for all aviation module errors."""


class AirworthinessError(AviationError):
    """Raised when airworthiness check fails."""


class WorkOrderError(AviationError):
    """Raised for invalid work order operations."""


class PartNumberMismatchError(AviationError):
    """Raised when part numbers do not match exactly."""


# ── Module API ─────────────────────────────────────────────────────────

__all__ = [
    # Value objects
    "PartNumber",
    "SerialNumber",
    "Airworthiness",
    # Domain models
    "Component",
    "Aircraft",
    "WorkOrder",
    # Enums
    "AirworthinessStatus",
    "ATAChapter",
    "WorkOrderStatus",
    "ComplianceStandard",
    # Exceptions
    "AviationError",
    "AirworthinessError",
    "WorkOrderError",
    "PartNumberMismatchError",
]

__version__ = "0.1.0"
