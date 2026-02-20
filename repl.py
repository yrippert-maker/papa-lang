#!/usr/bin/env python3
"""
PAPA Lang REPL — Interactive Console v0.4
$ papa repl
"""

import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.lexer import lex, LexerError
from src.parser import parse, ParseError
from src.interpreter import Interpreter, PapaError, FailSignal

# Try readline for history and completion
try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False

BANNER = """
🛡️ PAPA Lang v0.4.0 — Interactive REPL
   Введите :help для справки, :exit для выхода

papa> """

HELP = """
📖 PAPA Lang — Краткая справка

  Переменные:
    name = "PAPA"              // иммутабельная
    mut counter = 0             // мутабельная

  Типы:
    42, 3.14, "текст", true, false, none

  Строки с подстановкой:
    say "Привет, {name}!"

  Функции:
    square(n: int) -> int = n * n
    greet(name: text)
      say "Привет, {name}!"

  Управление:
    if x > 0
      say "положительное"
    else
      say "неположительное"

    for i in 1..5
      say "{i}"

  Безопасность:
    maybe_val = some(42)        // maybe тип
    val = maybe_val ?? 0        // значение по умолчанию
    pw = secret("my_pass")     // никогда не утечёт в лог

  Вывод:
    say "Hello!"                // печать
    log "сообщение"             // структурированный лог
"""

REPL_COMMANDS = """
  :help   — эта справка
  :vars   — показать переменные
  :funcs  — показать функции
  :clear  — очистить экран (или Ctrl+L)
  :reset  — сбросить состояние
  :load <file> — загрузить .papa файл
  :exit   — выход
"""


def _setup_readline():
    if not READLINE_AVAILABLE:
        return
    readline.parse_and_bind("tab: complete")
    hist_path = os.path.expanduser("~/.papa_history")
    try:
        readline.read_history_file(hist_path)
    except FileNotFoundError:
        pass

    def save_history():
        try:
            readline.write_history_file(hist_path)
        except Exception:
            pass

    import atexit
    atexit.register(save_history)


def _setup_completer(interp):
    if not READLINE_AVAILABLE:
        return

    def complete(text, state):
        names = []
        # Variables and functions
        for k in interp.global_env.vars:
            if k.startswith(text):
                names.append(k)
        for k in interp.global_env.functions:
            if k.startswith(text) and k not in names:
                names.append(k)
        for k in ["say", "log", "if", "else", "for", "true", "false", "some", "none", "secret"]:
            if k.startswith(text) and k not in names:
                names.append(k)
        names.sort()
        if state < len(names):
            return names[state]
        return None

    readline.set_completer(complete)


def _is_continuation(line: str) -> bool:
    """Строка требует продолжения (заканчивается на :, открыта скобка)."""
    s = line.strip()
    if s.endswith(":") and not s.startswith("//"):
        return True
    opens = s.count("(") - s.count(")")
    if opens > 0:
        return True
    return False


def main():
    print(BANNER)
    _setup_readline()
    interp = Interpreter()
    multiline = []
    in_block = False

    while True:
        try:
            prompt = "...  " if in_block else "papa> "
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print("\n\n  👋 До встречи!\n")
            break

        _setup_completer(interp)

        stripped = line.strip()

        # Команды :cmd и .cmd
        if stripped.startswith(":") or stripped.startswith("."):
            cmd = stripped.lstrip(":.").split()
            if not cmd:
                continue
            name = cmd[0].lower()
            if name == "exit" or name == "quit":
                print("\n  👋 До встречи!\n")
                break
            if name == "help":
                print(HELP)
                print(REPL_COMMANDS)
                continue
            if name == "vars":
                for k, v in interp.global_env.vars.items():
                    mut = "mut " if k in interp.global_env.mutables else ""
                    print(f"  \033[92m{mut}{k}\033[0m = {v!r}")
                print()
                continue
            if name == "funcs":
                for k, fn in interp.global_env.functions.items():
                    params = ", ".join(f"{p[0]}:{p[1] or 'any'}" for p in fn.params)
                    ret = f" -> {fn.return_type}" if fn.return_type else ""
                    print(f"  \033[92m{k}\033[0m({params}){ret}")
                print()
                continue
            if name == "clear":
                os.system("clear" if os.name != "nt" else "cls")
                continue
            if name == "reset":
                interp = Interpreter()
                print("  🔄 Состояние сброшено\n")
                continue
            if name == "load" and len(cmd) > 1:
                fname = cmd[1]
                if not os.path.exists(fname):
                    print(f"\033[91m  Файл не найден: {fname}\033[0m")
                else:
                    try:
                        with open(fname, "r", encoding="utf-8") as f:
                            src = f.read()
                        tokens = lex(src, fname)
                        ast = parse(tokens, src)
                        interp.interpret(ast, fname)
                        print(f"\033[92m  Загружен {fname}\033[0m\n")
                    except Exception as e:
                        print(f"\033[91m  Ошибка: {e}\033[0m")
                continue
            continue

        # Многострочный ввод
        if _is_continuation(line):
            multiline.append(line)
            in_block = True
            continue
        if in_block:
            multiline.append(line)
            full = "\n".join(multiline)
            if _is_continuation(full):
                continue
            in_block = False
            source = full
            multiline = []
        elif stripped == "" and multiline:
            in_block = False
            source = "\n".join(multiline)
            multiline = []
        else:
            source = line

        if not source.strip():
            continue

        try:
            tokens = lex(source)
            ast = parse(tokens, source)
            result = interp.interpret(ast)
            if result is not None:
                if not (source.strip().startswith("say ") or source.strip().startswith("log")):
                    print(f"  \033[92m→\033[0m {result!r}")
        except LexerError as e:
            print(f"\033[91m{e}\033[0m")
        except ParseError as e:
            print(f"\033[91m{e}\033[0m")
        except PapaError as e:
            print(f"\033[91m{e}\033[0m")
        except FailSignal as e:
            print(f"\033[93m{e}\033[0m")
        except Exception as e:
            print(f"\033[91m  Внутренняя ошибка: {e}\033[0m")


if __name__ == "__main__":
    main()
