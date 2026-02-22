"""
PAPA Lang AST — Abstract Syntax Tree nodes
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any


@dataclass
class Node:
    line: int = 0
    col: int = 0


# ── Expressions ──

@dataclass
class IntLiteral(Node):
    value: int = 0

@dataclass
class FloatLiteral(Node):
    value: float = 0.0

@dataclass
class TextLiteral(Node):
    value: str = ""
    interpolations: List[Any] = field(default_factory=list)

@dataclass
class BoolLiteral(Node):
    value: bool = False

@dataclass
class NoneLiteral(Node):
    pass

@dataclass
class Identifier(Node):
    name: str = ""

@dataclass
class BinaryOp(Node):
    left: Any = None
    op: str = ""
    right: Any = None

@dataclass
class UnaryOp(Node):
    op: str = ""
    operand: Any = None

@dataclass
class FunctionCall(Node):
    name: Any = None          # can be Identifier or MemberAccess
    args: List[Any] = field(default_factory=list)
    named_args: dict = field(default_factory=dict)

@dataclass
class MemberAccess(Node):
    object: Any = None
    member: str = ""

@dataclass
class OptionalChain(Node):
    """obj?.member"""
    object: Any = None
    member: str = ""

@dataclass
class NullCoalesce(Node):
    """expr ?? default"""
    expr: Any = None
    default: Any = None

@dataclass
class ListLiteral(Node):
    elements: List[Any] = field(default_factory=list)

@dataclass
class MapLiteral(Node):
    pairs: List[tuple] = field(default_factory=list)

@dataclass
class RangeLiteral(Node):
    start: Any = None
    end: Any = None

@dataclass
class IndexAccess(Node):
    object: Any = None
    index: Any = None


# ── Statements ──

@dataclass
class Assignment(Node):
    name: str = ""
    value: Any = None
    mutable: bool = False
    type_annotation: Optional[str] = None

@dataclass
class Reassignment(Node):
    target: Any = None
    value: Any = None

@dataclass
class SayStatement(Node):
    """say "text" — print to stdout"""
    expr: Any = None

@dataclass
class LogStatement(Node):
    """log "message" — structured logging"""
    level: str = "info"
    expr: Any = None

@dataclass
class ReturnStatement(Node):
    value: Any = None

@dataclass
class FailStatement(Node):
    message: Any = None

@dataclass
class BreakStatement(Node):
    pass

@dataclass
class IfStatement(Node):
    condition: Any = None
    body: List[Any] = field(default_factory=list)
    elif_branches: List[tuple] = field(default_factory=list)
    else_body: List[Any] = field(default_factory=list)

@dataclass
class MatchStatement(Node):
    expr: Any = None
    arms: List[tuple] = field(default_factory=list)  # (pattern, body)

@dataclass
class ForLoop(Node):
    var: str = ""
    iterable: Any = None
    body: List[Any] = field(default_factory=list)
    index_var: Optional[str] = None


@dataclass
class EnumDef(Node):
    name: str = ""
    variants: list = field(default_factory=list)

@dataclass
class LoopStatement(Node):
    body: List[Any] = field(default_factory=list)

@dataclass
class RepeatStatement(Node):
    count: Any = None
    body: List[Any] = field(default_factory=list)
    else_body: List[Any] = field(default_factory=list)

@dataclass
class WaitStatement(Node):
    duration: Any = None
    unit: str = "seconds"

@dataclass
class AssertStatement(Node):
    expr: Any = None
    message: Optional[str] = None


@dataclass
class TryCatchNode(Node):
    """try body catch err body"""
    try_body: List[Any] = field(default_factory=list)
    catch_var: str = ""
    catch_body: List[Any] = field(default_factory=list)


# ── Definitions ──

@dataclass
class FunctionDef(Node):
    name: str = ""
    params: List[tuple] = field(default_factory=list)  # (name, type, default)
    return_type: Optional[str] = None
    can_fail: bool = False
    is_async: bool = False
    body: List[Any] = field(default_factory=list)

@dataclass
class TypeDef(Node):
    name: str = ""
    fields: List[tuple] = field(default_factory=list)  # (name, type, default, modifiers)
    variants: List[tuple] = field(default_factory=list)  # for enum types

@dataclass
class ModelDef(Node):
    name: str = ""
    table: str = ""
    fields: List[tuple] = field(default_factory=list)
    indexes: List[Any] = field(default_factory=list)
    relations: List[tuple] = field(default_factory=list)

@dataclass
class RouteDef(Node):
    method: str = ""
    path: str = ""
    auth_required: bool = False
    input_fields: List[tuple] = field(default_factory=list)
    body: List[Any] = field(default_factory=list)

@dataclass
class ServeDef(Node):
    port: int = 8200
    host: str = "localhost"
    options: dict = field(default_factory=dict)

@dataclass
class TestDef(Node):
    name: str = ""
    body: List[Any] = field(default_factory=list)

@dataclass
class TaskDef(Node):
    name: str = ""
    body: List[Any] = field(default_factory=list)

@dataclass
class EveryDef(Node):
    interval: Any = None
    unit: str = ""
    body: List[Any] = field(default_factory=list)


# ── Top-level ──

@dataclass
class Program(Node):
    statements: List[Any] = field(default_factory=list)


# ── Import (v0.3) ──

@dataclass
class ImportStatement(Node):
    path: str = ""  # "path/to/file.papa"


@dataclass
class FromImportStatement(Node):
    path: str = ""
    names: List[str] = field(default_factory=list)  # [func1, func2]
