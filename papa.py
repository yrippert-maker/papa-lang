#!/usr/bin/env python3
"""
PAPA Lang CLI — One command for everything.

Usage:
  papa run <file.papa>     Run a PAPA Lang program
  papa serve <file.papa>   Run and start HTTP server
  papa repl                Start interactive console
  papa test <file.papa>    Run tests in a file
  papa init                Create papa.toml
  papa install [path]      Install package(s)
  papa list                List installed packages
  papa uninstall <name>    Remove package
  papa lex <file.papa>     Show tokens (debug)
  papa ast <file.papa>     Show AST (debug)
  papa version             Show version
  papa evolve [analyze|suggest|run|pr]  Self-evolving codebase
  papa marketplace           List MCP packages
"""

import os
import signal
import sys

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.lexer import lex, LexerError
from src.parser import parse, ParseError
from src.interpreter import Interpreter, PapaError, FailSignal

_current_interp = None


def _on_signal(signum, frame):
    global _current_interp
    if _current_interp:
        _current_interp.shutdown()
    sys.exit(128 + (signum if signum else 0))


def cmd_run(filename: str):
    """Run a .papa file."""
    if not os.path.exists(filename):
        print(f"\n── ОШИБКА ──\n\n  Файл не найден: {filename}\n")
        sys.exit(1)

    with open(filename, 'r') as f:
        source = f.read()

    global _current_interp
    interp = None
    try:
        signal.signal(signal.SIGINT, _on_signal)
        signal.signal(signal.SIGTERM, _on_signal)
        tokens = lex(source, filename)
        ast = parse(tokens, source)
        interp = Interpreter()
        _current_interp = interp
        interp.interpret(ast, filename)

        # Run tests if any
        if interp.tests:
            print(f"\n🧪 Запуск тестов ({len(interp.tests)}):\n")
            passed, failed, _ = interp.run_tests()
            if failed > 0:
                sys.exit(1)

    except (LexerError, ParseError, PapaError) as e:
        print(f"\033[91m{e}\033[0m")
        sys.exit(1)
    except FailSignal as e:
        print(f"\033[93m{e}\033[0m")
        sys.exit(1)
    finally:
        _current_interp = None
        if interp:
            interp.shutdown()


def cmd_serve(filename: str):
    """Run a .papa file and start HTTP server."""
    if not os.path.exists(filename):
        print(f"\n── ОШИБКА ──\n\n  Файл не найден: {filename}\n")
        sys.exit(1)

    with open(filename, 'r') as f:
        source = f.read()

    global _current_interp
    interp = None
    try:
        signal.signal(signal.SIGINT, _on_signal)
        signal.signal(signal.SIGTERM, _on_signal)
        tokens = lex(source, filename)
        ast = parse(tokens, source)
        interp = Interpreter()
        _current_interp = interp
        interp.interpret(ast, filename)

        if not interp.serve_config:
            print("\n── ОШИБКА ──\n\n  В файле нет 'serve on port N'. Добавьте конфигурацию сервера.\n")
            sys.exit(1)

        interp.start_server()
    except (LexerError, ParseError, PapaError) as e:
        print(f"\033[91m{e}\033[0m")
        sys.exit(1)
    except FailSignal as e:
        print(f"\033[93m{e}\033[0m")
        sys.exit(1)
    finally:
        _current_interp = None
        if interp:
            interp.shutdown()


def cmd_test(filename: str):
    """Run only tests from a .papa file."""
    if not os.path.exists(filename):
        print(f"\n── ОШИБКА ──\n\n  Файл не найден: {filename}\n")
        sys.exit(1)

    with open(filename, 'r') as f:
        source = f.read()

    global _current_interp
    interp = None
    try:
        signal.signal(signal.SIGINT, _on_signal)
        signal.signal(signal.SIGTERM, _on_signal)
        tokens = lex(source, filename)
        ast = parse(tokens, source)
        interp = Interpreter()
        _current_interp = interp
        interp.interpret(ast, filename)

        if not interp.tests:
            print("  Тесты не найдены.")
            return

        print(f"\n🧪 Запуск тестов ({len(interp.tests)}):\n")
        passed, failed, _ = interp.run_tests()
        if failed > 0:
            sys.exit(1)

    except (LexerError, ParseError, PapaError) as e:
        print(f"\033[91m{e}\033[0m")
        sys.exit(1)
    finally:
        _current_interp = None
        if interp:
            interp.shutdown()


def cmd_lex(filename: str):
    """Show tokens for debugging."""
    with open(filename, 'r') as f:
        source = f.read()

    tokens = lex(source, filename)
    for tok in tokens:
        print(f"  {tok}")


def cmd_ast(filename: str):
    """Show AST for debugging."""
    with open(filename, 'r') as f:
        source = f.read()

    tokens = lex(source, filename)
    ast = parse(tokens, source)
    _print_ast(ast, 0)


def _print_ast(node, indent):
    prefix = "  " * indent
    name = type(node).__name__
    if hasattr(node, 'name') and isinstance(getattr(node, 'name'), str):
        print(f"{prefix}{name}({node.name})")
    elif hasattr(node, 'value'):
        print(f"{prefix}{name}({node.value!r})")
    elif hasattr(node, 'op'):
        print(f"{prefix}{name}({node.op})")
    else:
        print(f"{prefix}{name}")

    # Print children
    for attr in ('statements', 'body', 'else_body', 'args', 'elements',
                 'left', 'right', 'operand', 'expr', 'condition',
                 'iterable', 'value', 'object', 'default'):
        val = getattr(node, attr, None)
        if val is None:
            continue
        if isinstance(val, list):
            for item in val:
                if hasattr(item, '__dataclass_fields__'):
                    _print_ast(item, indent + 1)
        elif hasattr(val, '__dataclass_fields__'):
            _print_ast(val, indent + 1)


def cmd_repl():
    """Start REPL."""
    from repl import main
    main()



def cmd_marketplace():
    """List MCP marketplace packages."""
    import json
    registry_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "marketplace_registry.json")
    if not os.path.isfile(registry_path):
        print("\n  Marketplace registry not found.\n")
        return
    with open(registry_path, "r", encoding="utf-8") as f:
        reg = json.load(f)
    print("\n  PAPA MCP Marketplace")
    print("  " + "=" * 40)
    for pkg in reg.get("packages", []):
        tier = pkg.get("tier", "free")
        print(f"  • {pkg.get('name')} [{tier}] — {pkg.get('description', '')[:50]}...")
    print()

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == 'version':
        print("PAPA Lang v0.8.0")
    elif cmd == 'init':
        from src.package_manager import PackageManager
        PackageManager().init()
    elif cmd == 'install':
        from src.package_manager import PackageManager
        pm = PackageManager()
        pm.install(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == 'list':
        from src.package_manager import PackageManager
        pkgs = PackageManager().list_packages()
        if not pkgs:
            print("  Пакеты не установлены (papa_modules/ пуст)")
        else:
            for name, ver in pkgs:
                print(f"  {name}" + (f" {ver}" if ver else ""))
    elif cmd == 'uninstall' and len(sys.argv) > 2:
        from src.package_manager import PackageManager
        PackageManager().uninstall(sys.argv[2])
    elif cmd == 'serve' and len(sys.argv) > 2:
        cmd_serve(sys.argv[2])
    elif cmd == 'repl':
        cmd_repl()
    elif cmd == 'run' and len(sys.argv) > 2:
        cmd_run(sys.argv[2])
    elif cmd == 'test' and len(sys.argv) > 2:
        cmd_test(sys.argv[2])
    elif cmd == 'lex' and len(sys.argv) > 2:
        cmd_lex(sys.argv[2])
    elif cmd == 'ast' and len(sys.argv) > 2:
        cmd_ast(sys.argv[2])
    elif cmd == 'marketplace':
        cmd_marketplace()
    elif cmd == 'evolve':
        from lib.cli_evolve import handle_evolve
        project_root = os.path.dirname(os.path.abspath(__file__))
        handle_evolve(sys.argv[2:] if len(sys.argv) > 2 else ['analyze'], project_root)
    elif cmd.endswith('.papa'):
        cmd_run(cmd)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
