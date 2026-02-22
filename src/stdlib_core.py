"""
PAPA Lang stdlib_core — math, string, json, http, fs, time.
"""

import json

import os
import math
import random
from typing import Any, Dict

from .environment import Maybe, Secret, PapaList, PapaMap


def _unwrap(val):
    """Recursively convert PapaMap/PapaList/Maybe to plain Python types.
    Used when passing PAPA values to Python-native std module implementations."""
    if val is None:
        return None
    # Maybe → unwrap or None
    if hasattr(val, '_has') and hasattr(val, '_value'):
        return _unwrap(val._value) if val._has else None
    # PapaMap → dict
    if hasattr(val, '_data') and isinstance(getattr(val, '_data', None), dict):
        return {k: _unwrap(v) for k, v in val._data.items()}
    # PapaList → list
    if hasattr(val, '_items') and isinstance(getattr(val, '_items', None), list):
        return [_unwrap(x) for x in val._items]
    # Plain Python types — pass through
    return val


def _to_json_value(val: Any) -> Any:
    """Convert PAPA value to JSON-serializable form."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float, str)):
        return val
    if isinstance(val, Maybe):
        if val.exists:
            return _to_json_value(val.value)
        return None
    if isinstance(val, Secret):
        return "***REDACTED***"
    if isinstance(val, PapaList):
        return [_to_json_value(x) for x in val._items]
    if isinstance(val, PapaMap):
        return {str(k): _to_json_value(v) for k, v in val._data.items()}
    if isinstance(val, dict):
        return {str(k): _to_json_value(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_to_json_value(x) for x in val]
    return str(val)


def _std_math(interp: 'Interpreter') -> Dict[str, Any]:
    """std/math — mathematical functions and constants."""
    builtins = interp.builtins
    prefix = "_math_"
    builtins[prefix + "sqrt"] = lambda args: math.sqrt(float(args[0]))
    builtins[prefix + "pow"] = lambda args: math.pow(float(args[0]), float(args[1])) if len(args) > 1 else math.pow(float(args[0]), 2)
    builtins[prefix + "floor"] = lambda args: math.floor(float(args[0]))
    builtins[prefix + "ceil"] = lambda args: math.ceil(float(args[0]))
    builtins[prefix + "round"] = lambda args: round(float(args[0]), int(args[1]) if len(args) > 1 else 0)
    builtins[prefix + "sin"] = lambda args: math.sin(float(args[0]))
    builtins[prefix + "cos"] = lambda args: math.cos(float(args[0]))
    builtins[prefix + "tan"] = lambda args: math.tan(float(args[0]))
    builtins[prefix + "ln"] = lambda args: math.log(float(args[0]))
    builtins[prefix + "log10"] = lambda args: math.log10(float(args[0]))
    builtins[prefix + "random"] = lambda args: random.random()
    builtins[prefix + "random_int"] = lambda args: random.randint(int(args[0]), int(args[1]))
    return {
        "sqrt": ("builtin", prefix + "sqrt"), "pow": ("builtin", prefix + "pow"),
        "floor": ("builtin", prefix + "floor"), "ceil": ("builtin", prefix + "ceil"),
        "round": ("builtin", prefix + "round"), "sin": ("builtin", prefix + "sin"),
        "cos": ("builtin", prefix + "cos"), "tan": ("builtin", prefix + "tan"),
        "ln": ("builtin", prefix + "ln"), "log10": ("builtin", prefix + "log10"),
        "random": ("builtin", prefix + "random"), "random_int": ("builtin", prefix + "random_int"),
        "pi": 3.141592653589793, "e": 2.718281828459045,
    }


def _std_string(interp: 'Interpreter') -> Dict[str, Any]:
    """std/string — string manipulation."""
    prefix = "_str_"
    interp.builtins[prefix + "trim"] = lambda args: str(args[0]).strip()
    interp.builtins[prefix + "upper"] = lambda args: str(args[0]).upper()
    interp.builtins[prefix + "lower"] = lambda args: str(args[0]).lower()
    interp.builtins[prefix + "starts_with"] = lambda args: str(args[0]).startswith(str(args[1]))
    interp.builtins[prefix + "ends_with"] = lambda args: str(args[0]).endswith(str(args[1]))
    interp.builtins[prefix + "contains"] = lambda args: str(args[1]) in str(args[0])
    interp.builtins[prefix + "replace"] = lambda args: str(args[0]).replace(str(args[1]), str(args[2]))
    interp.builtins[prefix + "split"] = lambda args: PapaList(str(args[0]).split(str(args[1]) if len(args) > 1 else None))
    interp.builtins[prefix + "join"] = lambda args: (str(args[1]) if len(args) > 1 else " ").join(str(x) for x in (_unwrap(args[0]) if args else []) or [])
    interp.builtins[prefix + "repeat_str"] = lambda args: str(args[0]) * int(args[1])
    interp.builtins[prefix + "reverse"] = lambda args: str(args[0])[::-1]
    interp.builtins[prefix + "char_at"] = lambda args: Maybe.some(str(args[0])[int(args[1])]) if 0 <= int(args[1]) < len(str(args[0])) else Maybe.none()
    interp.builtins[prefix + "pad_left"] = lambda args: str(args[0]).rjust(int(args[1]), str(args[2]) if len(args) > 2 else " ")
    interp.builtins[prefix + "pad_right"] = lambda args: str(args[0]).ljust(int(args[1]), str(args[2]) if len(args) > 2 else " ")
    return {k: ("builtin", prefix + k) for k in ["trim", "upper", "lower", "starts_with", "ends_with", "contains",
        "replace", "split", "join", "repeat_str", "reverse", "char_at", "pad_left", "pad_right"]}


def _std_json(interp: 'Interpreter') -> Dict[str, Any]:
    """std/json — JSON encode/decode."""
    prefix = "_json_"
    def encode(args):
        v = args[0]
        return json.dumps(_to_json_value(v), ensure_ascii=False)
    def decode(args):
        try:
            data = json.loads(str(args[0]))
            return interp._py_to_papa(data)
        except Exception:
            return Maybe.none()
    def pretty(args):
        return json.dumps(_to_json_value(args[0]), ensure_ascii=False, indent=2)
    interp.builtins[prefix + "encode"] = encode
    interp.builtins[prefix + "decode"] = decode
    interp.builtins[prefix + "pretty"] = pretty
    return {"json_encode": ("builtin", prefix + "encode"), "json_decode": ("builtin", prefix + "decode"),
            "json_pretty": ("builtin", prefix + "pretty")}


def _std_http(interp: 'Interpreter') -> Dict[str, Any]:
    """std/http — HTTP client via urllib."""
    import urllib.request
    prefix = "_http_"
    def do_request(method, url, body=None):
        try:
            req = urllib.request.Request(url, data=body.encode() if body else None, method=method)
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=10) as r:
                return Maybe.some(PapaMap([("status", r.getcode()), ("body", r.read().decode()),
                    ("headers", PapaMap([(k, v) for k, v in r.headers.items()]))]))
        except Exception:
            return Maybe.none()
    interp.builtins[prefix + "get"] = lambda args: do_request("GET", str(args[0]))
    interp.builtins[prefix + "post"] = lambda args: do_request("POST", str(args[0]), str(args[1]) if len(args) > 1 else None)
    interp.builtins[prefix + "put"] = lambda args: do_request("PUT", str(args[0]), str(args[1]) if len(args) > 1 else None)
    interp.builtins[prefix + "delete"] = lambda args: do_request("DELETE", str(args[0]))
    return {"http_get": ("builtin", prefix + "get"), "http_post": ("builtin", prefix + "post"),
            "http_put": ("builtin", prefix + "put"), "http_delete": ("builtin", prefix + "delete")}


def _std_fs(interp: 'Interpreter') -> Dict[str, Any]:
    """std/fs — file system."""
    prefix = "_fs_"
    def read(args):
        try:
            with open(str(args[0]), 'r', encoding='utf-8') as f:
                return Maybe.some(f.read())
        except Exception:
            return Maybe.none()
    def write(args):
        with open(str(args[0]), 'w', encoding='utf-8') as f:
            f.write(str(args[1]))
    interp.builtins[prefix + "read"] = read
    interp.builtins[prefix + "write"] = write
    interp.builtins[prefix + "exists"] = lambda args: os.path.exists(str(args[0]))
    interp.builtins[prefix + "list_dir"] = lambda args: PapaList(os.listdir(str(args[0])))
    interp.builtins[prefix + "delete"] = lambda args: os.remove(str(args[0]))
    return {"read_file": ("builtin", prefix + "read"), "write_file": ("builtin", prefix + "write"),
            "file_exists": ("builtin", prefix + "exists"), "list_dir": ("builtin", prefix + "list_dir"),
            "delete_file": ("builtin", prefix + "delete")}


def _std_time(interp: 'Interpreter') -> Dict[str, Any]:
    """std/time — time utilities."""
    import time
    prefix = "_time_"
    interp.builtins[prefix + "timestamp"] = lambda args: time.time()
    interp.builtins[prefix + "format_time"] = lambda args: time.strftime(str(args[0]) if args else "%Y-%m-%d %H:%M:%S", time.localtime())
    return {"timestamp": ("builtin", prefix + "timestamp"), "format_time": ("builtin", prefix + "format_time")}


__all__ = [
    '_unwrap', '_to_json_value',
    '_std_math', '_std_string', '_std_json', '_std_http', '_std_fs', '_std_time',
]
