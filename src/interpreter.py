"""
PAPA Lang Interpreter — Executes AST
Built-in safety: no null crashes, secret redaction, friendly errors.
v0.3: HTTP server, imports, async, models.
v0.4: Full std library (math, string, json, http, fs, time).
"""

import os
import time
from typing import Any, Dict, List, Optional, Set

from .ast_nodes import Program, RouteDef, TestDef, ServeDef
from .environment import (
    Environment, Maybe, PapaList, PapaMap, Secret,
    PapaError, FailSignal, ReturnSignal,
)
from .stdlib_core import _std_math, _std_string, _std_json, _std_http, _std_fs, _std_time
from .stdlib_agents import (
    _std_voice, _std_mcp, _std_browser, _std_telegram, _std_ai_budget, _std_design,
)
from .stdlib_enterprise import _load_orchestrator, _load_docs, _load_studio, _load_cwb
from .papa_lang_wave2_wave3_modules import WAVE_2_3_LOADERS
from .server import start_server as _start_server
from .evaluator import EvaluatorMixin
from .executor import ExecutorMixin


STD_MODULE_LOADERS = {
    "math": _std_math,
    "string": _std_string,
    "json": _std_json,
    "http": _std_http,
    "fs": _std_fs,
    "time": _std_time,
    "voice": _std_voice,
    "mcp": _std_mcp,
    "browser": _std_browser,
    "telegram": _std_telegram,
    "ai": _std_ai_budget,
    "ai_budget": _std_ai_budget,
    "design": _std_design,
    "orchestrator": _load_orchestrator,
    "docs": _load_docs,
    "studio": _load_studio,
    "cwb": _load_cwb,
    **WAVE_2_3_LOADERS,
}


class Interpreter(EvaluatorMixin, ExecutorMixin):
    def __init__(self):
        self.global_env = Environment()
        self.output: List[str] = []
        self.routes: Dict[str, RouteDef] = {}
        self.tests: List[TestDef] = []
        self.serve_config: Optional[ServeDef] = None
        self.tasks: List[Any] = []
        self._timers: List[Any] = []
        self._imported_files: Set[str] = set()
        self._loaded_modules: Dict[str, Any] = {}
        self._loading_stack: List[str] = []
        self._current_file_dir: str = ""
        self._setup_builtins()

    def _ask_impl(self, args: List[Any]) -> str:
        """ask(prompt) or ask(model, prompt) — call AI API."""
        if not args:
            return "[AI not available — provide a prompt]"
        model = "claude-sonnet-4-20250514"
        prompt = str(args[0])
        if len(args) >= 2:
            model_str = str(args[0]).lower()
            prompt = str(args[1])
            if "gpt" in model_str or "openai" in model_str:
                model = "gpt-4o"
            elif "claude" in model_str:
                model = "claude-sonnet-4-20250514"
            elif "gemini" in model_str:
                model = "gemini-1.5-pro"
        api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return "[AI not available — set ANTHROPIC_API_KEY or OPENAI_API_KEY]"
        try:
            import json
            import urllib.request
            if "claude" in model or "anthropic" in model.lower():
                req = urllib.request.Request(
                    "https://api.anthropic.com/v1/messages",
                    data=json.dumps({
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 1024,
                        "messages": [{"role": "user", "content": prompt}],
                    }).encode(),
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json.loads(r.read().decode())
                    for b in data.get("content", []):
                        if b.get("type") == "text":
                            return b.get("text", "")
            elif "gpt" in model:
                req = urllib.request.Request(
                    "https://api.openai.com/v1/chat/completions",
                    data=json.dumps({
                        "model": "gpt-4o",
                        "max_tokens": 1024,
                        "messages": [{"role": "user", "content": prompt}],
                    }).encode(),
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "content-type": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json.loads(r.read().decode())
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            return f"[AI error: {e}]"
        return "[AI not available]"

    def _agent_from_args(self, args: List[Any]) -> Any:
        """agent(model, prompt) or agent({model, prompt}) — create agent with .run(input)."""
        if len(args) >= 2:
            model = str(args[0])
            prompt = str(args[1])
        elif args and hasattr(args[0], "_data"):
            cfg = args[0]._data
            model = str(cfg.get("model", "claude-sonnet"))
            prompt = str(cfg.get("prompt", ""))
        else:
            return PapaMap()
        agent_map = PapaMap([("model", model), ("prompt", prompt)])
        _self = self

        def agent_run(input_args):
            inp = str(input_args[0]) if input_args else ""
            return _self._ask_impl([model, f"{prompt}\n\nUser input:\n{inp}"])

        agent_map.run = agent_run
        return agent_map

    def _setup_builtins(self):
        """Register built-in functions."""
        self.builtins = {
            'abs': lambda args: abs(args[0]),
            'max': lambda args: max(args[0], args[1]) if len(args) > 1 else max(args[0]),
            'min': lambda args: min(args[0], args[1]) if len(args) > 1 else min(args[0]),
            'len': lambda args: len(args[0]) if hasattr(args[0], '__len__') else args[0].count,
            'str': lambda args: str(args[0]),
            'int': lambda args: int(args[0]),
            'float': lambda args: float(args[0]),
            'range': lambda args: PapaList(range(int(args[0]), int(args[1]) + 1) if len(args) > 1 else range(int(args[0]))),
            'type_of': lambda args: type(args[0]).__name__,
            'some': lambda args: Maybe.some(args[0]),
            'none': lambda args: Maybe.none(),
            'secret': lambda args: Secret(str(args[0])),
            'list': lambda args: PapaList(args[0] if args else []),
            'map': lambda args: PapaMap(),
            'print': lambda args: self._builtin_print(args),
            'input': lambda args: input(args[0] if args else ""),
            'sleep': lambda args: time.sleep(args[0]),
            'now': lambda args: time.strftime("%Y-%m-%d %H:%M:%S"),
            'env': lambda args: self._env_get(args[0]),
            'assert_eq': lambda args: self._builtin_assert_eq(args),
            'assert_true': lambda args: self._builtin_assert_true(args),
            'assert_false': lambda args: self._builtin_assert_false(args),
            'ask': lambda args: self._ask_impl(args),
            'agent': lambda args: self._agent_from_args(args),
        }

    def _builtin_print(self, args):
        text = ' '.join(str(a) for a in args)
        self.output.append(text)
        print(text)
        return None

    def _unwrap_for_compare(self, v):
        if hasattr(v, 'value'):
            return v.value
        return v

    def _builtin_assert_eq(self, args):
        if len(args) < 2:
            raise FailSignal("assert_eq требует 2 аргумента")
        a, b = self._unwrap_for_compare(args[0]), self._unwrap_for_compare(args[1])
        if a != b:
            raise FailSignal(f"assert_eq: ожидалось {a!r}, получено {b!r}")

    def _builtin_assert_true(self, args):
        if not args:
            raise FailSignal("assert_true требует 1 аргумент")
        v = self._unwrap_for_compare(args[0])
        if not v:
            raise FailSignal(f"assert_true: ожидалось True, получено {v!r}")

    def _builtin_assert_false(self, args):
        if not args:
            raise FailSignal("assert_false требует 1 аргумент")
        v = self._unwrap_for_compare(args[0])
        if v:
            raise FailSignal(f"assert_false: ожидалось False, получено {v!r}")

    def _env_get(self, name):
        val = os.environ.get(name)
        if val:
            return Maybe.some(val)
        return Maybe.none()

    def interpret(self, program: Program, filename: str = "") -> Any:
        if filename:
            self._current_file_dir = os.path.dirname(os.path.abspath(filename))
        result = None
        for stmt in program.statements:
            result = self.execute(stmt, self.global_env)
        return result

    def execute(self, node: Any, env: Environment) -> Any:
        if node is None:
            return None
        method_name = f'exec_{type(node).__name__}'
        method = getattr(self, method_name, None)
        if method:
            return method(node, env)
        return self.evaluate(node, env)

    def evaluate(self, node: Any, env: Environment) -> Any:
        if node is None:
            return None
        method_name = f'eval_{type(node).__name__}'
        method = getattr(self, method_name, None)
        if method:
            return method(node, env)
        raise PapaError(f"Не могу вычислить: {type(node).__name__}", getattr(node, 'line', 0))

    def _resolve_import_path(self, path: str) -> tuple:
        if path.startswith("std/"):
            name = path[4:].split("/")[0].split(".")[0]
            if name in STD_MODULE_LOADERS:
                return ("std", name, None)
            raise PapaError(
                f"Стандартный модуль '{path}' не найден",
                hint="Доступны: std/math, std/string, std/json, std/http, std/fs, std/time, std/voice, std/mcp, std/browser, std/telegram, std/ai, std/design, std/orchestrator, std/docs, std/studio, std/cwb, std/guard, std/ai_router, std/evolve, std/swarm, std/infra, std/gemini, std/verify, std/chain, std/voice_prog"
            )
        base = self._current_file_dir or os.getcwd()
        full = os.path.normpath(os.path.join(base, path))
        if not full.endswith('.papa'):
            full += '.papa'
        if os.path.exists(full):
            return ("file", full, full)
        proj_root = self._find_project_root(base)
        if proj_root:
            parts = path.replace("\\", "/").split("/")
            pkg_dir = os.path.join(proj_root, "papa_modules", parts[0])
            if len(parts) == 1:
                idx = os.path.join(pkg_dir, "index.papa")
                if os.path.isfile(idx):
                    return ("file", idx, idx)
                if os.path.isfile(pkg_dir + ".papa"):
                    return ("file", pkg_dir + ".papa", pkg_dir + ".papa")
            else:
                subpath = os.path.join(pkg_dir, *parts[1:])
                if not subpath.endswith(".papa"):
                    subpath += ".papa"
                if os.path.isfile(subpath):
                    return ("file", subpath, subpath)
        raise PapaError(
            f"Модуль не найден: {path}",
            hint=f"Проверьте путь или papa install <package>"
        )

    def _find_project_root(self, start: str) -> Optional[str]:
        current = os.path.abspath(start)
        while current and current != os.path.dirname(current):
            if os.path.isfile(os.path.join(current, "papa.toml")):
                return current
            if os.path.isdir(os.path.join(current, "papa_modules")):
                return current
            current = os.path.dirname(current)
        return None

    def _load_module(self, path: str) -> tuple:
        resolved = self._resolve_import_path(path)
        if resolved[0] == "std":
            _, name, _ = resolved
            cache_key = "std:" + name
            if cache_key in self._loaded_modules:
                return self._loaded_modules[cache_key], path
            if cache_key in self._loading_stack:
                raise PapaError(
                    f"Циклический импорт: {path}",
                    hint="Уберите циклическую зависимость между файлами"
                )
            self._loading_stack.append(cache_key)
            import_env = Environment(parent=self.global_env)
            exports = STD_MODULE_LOADERS[name](self)
            for k, v in exports.items():
                if isinstance(v, tuple) and v[0] == "builtin":
                    import_env.vars[k] = v
                else:
                    import_env.vars[k] = v
            self._loading_stack.pop()
            self._loaded_modules[cache_key] = import_env
            return import_env, path

        full_path = resolved[2]
        if full_path in self._loaded_modules:
            return self._loaded_modules[full_path], path
        if full_path in self._loading_stack:
            raise PapaError(
                f"Циклический импорт: {path}",
                hint="Уберите циклическую зависимость между файлами"
            )
        self._loading_stack.append(full_path)
        with open(full_path, 'r', encoding='utf-8') as f:
            source = f.read()
        from .lexer import lex
        from .parser import parse
        tokens = lex(source, full_path)
        ast = parse(tokens, source)
        import_env = Environment(parent=self.global_env)
        orig_dir = self._current_file_dir
        self._current_file_dir = os.path.dirname(full_path)
        try:
            for stmt in ast.statements:
                self.execute(stmt, import_env)
        finally:
            self._current_file_dir = orig_dir
            self._loading_stack.pop()
        self._loaded_modules[full_path] = import_env
        return import_env, path

    def shutdown(self) -> None:
        """Cancel timers and cleanup (graceful shutdown)."""
        for t in getattr(self, '_timers', []):
            try:
                t.cancel()
            except Exception:
                pass
        self._timers.clear()
        from .environment import PapaModel
        if getattr(PapaModel, '_conn', None):
            PapaModel._conn.close()
            PapaModel._conn = None

    def run_tests(self) -> tuple:
        passed = 0
        failed = 0
        results = []
        for test in self.tests:
            test_env = Environment(parent=self.global_env)
            try:
                for stmt in test.body:
                    self.execute(stmt, test_env)
                passed += 1
                results.append(('✅', test.name, None))
                print(f"  ✅ {test.name}")
            except Exception as e:
                failed += 1
                results.append(('❌', test.name, str(e)))
                print(f"  ❌ {test.name}: {e}")
        print(f"\n  Результат: {passed} прошло, {failed} провалено")
        return passed, failed, results

    def _py_to_papa(self, val: Any) -> Any:
        if val is None:
            return Maybe.none()
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return val
        if isinstance(val, str):
            return val
        if isinstance(val, list):
            return PapaList([self._py_to_papa(x) for x in val])
        if isinstance(val, dict):
            return PapaMap([(k, self._py_to_papa(v)) for k, v in val.items()])
        return val

    def start_server(self):
        _start_server(self)


def run(source: str, filename: str = "<stdin>") -> Interpreter:
    from .lexer import lex
    from .parser import parse

    tokens = lex(source, filename)
    ast = parse(tokens, source)
    interp = Interpreter()
    interp.interpret(ast)
    return interp
