"""CLI entry point: papa compile/validate/init."""

import argparse
import pathlib
import sys

from .lexer import Lexer, LexError
from .parser import Parser, ParseError
from .validator import Validator, ValidationError
from .codegen.python_gen import PythonGenerator
from .codegen.ts_gen import TypeScriptGenerator


def cmd_compile(args: argparse.Namespace) -> None:
    source = pathlib.Path(args.file).read_text()
    src_path = pathlib.Path(args.file)
    try:
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse(source_file=src_path.name)
        warnings = Validator().validate(program)
        for w in warnings:
            print(f"⚠️ {w}")
        if args.target == "python":
            out = PythonGenerator().generate(program, source_file=src_path.name)
            ext = ".py"
        else:
            out = TypeScriptGenerator().generate(program, source_file=src_path.name)
            ext = ".ts"
        out_file = src_path.stem + "_compiled" + ext
        pathlib.Path(out_file).write_text(out)
        print(f"✅ Compiled: {out_file}")
    except (LexError, ParseError, ValidationError) as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)


def cmd_validate(args: argparse.Namespace) -> None:
    source = pathlib.Path(args.file).read_text()
    try:
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        warnings = Validator().validate(program)
        for w in warnings:
            print(f"⚠️ {w}")
        if not warnings:
            print("✅ Valid")
    except (LexError, ParseError, ValidationError) as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)


def cmd_init(args: argparse.Namespace) -> None:
    name = args.name
    template = f"""# {name}.papa
agent main {{
  model: claude-3-sonnet
  guard: standard
  hrs_threshold: 0.15
}}

pipeline main {{
  route: orchestrator
  fallback: single
}}
"""
    pathlib.Path(f"{name}.papa").write_text(template)
    print(f"✅ Created: {name}.papa")


def main() -> None:
    parser = argparse.ArgumentParser(prog="papa")
    sub = parser.add_subparsers()
    c = sub.add_parser("compile")
    c.add_argument("file")
    c.add_argument("--target", choices=["python", "typescript"], default="python")
    c.set_defaults(func=cmd_compile)
    v = sub.add_parser("validate")
    v.add_argument("file")
    v.set_defaults(func=cmd_validate)
    i = sub.add_parser("init")
    i.add_argument("name")
    i.set_defaults(func=cmd_init)
    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
