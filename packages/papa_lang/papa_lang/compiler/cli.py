"""CLI entry point: papa compile/validate/init."""

import argparse
import pathlib
import sys

from .lexer import Lexer, LexError
from .parser import Parser, ParseError
from .validator import Validator, ValidationError
from .codegen.python_gen import PythonGenerator
from .codegen.ts_gen import TypeScriptGenerator
from .codegen.crewai_gen import generate_crewai
from .codegen.dotnet_gen import generate_dotnet


TARGETS = {
    "python": (PythonGenerator().generate, "_compiled.py"),
    "typescript": (TypeScriptGenerator().generate, "_compiled.ts"),
    "crewai": (
        lambda p, source_file="": generate_crewai(p, source_file),
        "_crew.py",
    ),
    "dotnet": (
        lambda p, source_file="": generate_dotnet(p, source_file),
        ".g.cs",
    ),
}


def cmd_compile(args: argparse.Namespace) -> None:
    source = pathlib.Path(args.file).read_text()
    src_path = pathlib.Path(args.file)
    try:
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse(source_file=src_path.name)
        warnings = Validator().validate(program)
        for w in warnings:
            print(f"⚠️ {w}")
        target = getattr(args, "target", "python")
        gen_fn, ext_suffix = TARGETS.get(target, TARGETS["python"])
        out = gen_fn(program, source_file=src_path.name)
        out_file = src_path.stem + ext_suffix
        pathlib.Path(out_file).write_text(out)
        print(f"✅ Compiled: {out_file}")

        if getattr(args, "kya", False):
            from papa_lang.kya import generate_kya, export_kya
            for agent in program.agents:
                kya_data = generate_kya(
                    agent, source, issued_by=getattr(args, "issued_by", "Unknown")
                )
                kya_path = export_kya(kya_data, src_path.with_name(agent.name))
                print(f"KYA artifact: {kya_path}")
    except (LexError, ParseError, ValidationError) as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)


def cmd_verify_kya(args: argparse.Namespace) -> None:
    from papa_lang.kya import verify_kya

    kya_file = pathlib.Path(args.kya_file)
    source_file = pathlib.Path(args.source_file)
    if not kya_file.exists():
        print(f"❌ KYA file not found: {kya_file}", file=sys.stderr)
        sys.exit(1)
    if not source_file.exists():
        print(f"❌ Source file not found: {source_file}", file=sys.stderr)
        sys.exit(1)
    ok = verify_kya(kya_file, source_file)
    print(f"KYA verification: {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)


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
    c.add_argument(
        "--target",
        choices=["python", "typescript", "crewai", "dotnet"],
        default="python",
    )
    c.add_argument("--kya", action="store_true", help="Also generate KYA artifact")
    c.add_argument("--issued-by", default="Unknown", help="KYA issuer (with --kya)")
    c.set_defaults(func=cmd_compile)
    vk = sub.add_parser("verify-kya")
    vk.add_argument("kya_file")
    vk.add_argument("source_file")
    vk.set_defaults(func=cmd_verify_kya)
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
