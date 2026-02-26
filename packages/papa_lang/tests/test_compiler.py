"""Tests for papa-lang compiler."""

import sys
import pytest
from pathlib import Path

# Add package to path for tests
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from papa_lang.compiler.lexer import Lexer, LexError
from papa_lang.compiler.parser import Parser, ParseError
from papa_lang.compiler.validator import Validator, ValidationError
from papa_lang.compiler.codegen.python_gen import PythonGenerator


def test_lexer_tokenizes_agent_block():
    tokens = Lexer("agent foo { model: claude-3 }").tokenize()
    types = [t.type for t in tokens]
    assert "KEYWORD" in types
    assert "IDENT" in types


def test_parser_builds_swarm_with_consensus():
    src = "agent a {} swarm s { agents: [a] consensus: 4/7 }"
    tokens = Lexer(src).tokenize()
    program = Parser(tokens).parse()
    assert len(program.swarms) == 1
    assert program.swarms[0].consensus is not None
    assert program.swarms[0].consensus.required == 4
    assert program.swarms[0].consensus.of == 7


def test_validator_undefined_agent_raises():
    src = "swarm s { agents: [undefined_agent] }"
    tokens = Lexer(src).tokenize()
    program = Parser(tokens).parse()
    with pytest.raises(ValidationError, match="not defined"):
        Validator().validate(program)


def test_validator_hrs_out_of_range_raises():
    src = "agent a { hrs_threshold: 1.5 }"
    tokens = Lexer(src).tokenize()
    program = Parser(tokens).parse()
    with pytest.raises(ValidationError, match="0.0-1.0"):
        Validator().validate(program)


def test_python_codegen_agent():
    src = "agent synthesis { model: gemini-1.5-pro guard: strict }"
    tokens = Lexer(src).tokenize()
    program = Parser(tokens).parse()
    code = PythonGenerator().generate(program)
    assert "SwarmAgent" in code
    assert "synthesis" in code
    assert "gemini-1.5-pro" in code


def test_full_roundtrip_papa_to_python(tmp_path):
    papa_file = tmp_path / "test.papa"
    papa_file.write_text(
        "agent a { guard: strict } pipeline p { route: orchestrator }"
    )
    import os
    from papa_lang.compiler.cli import main

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        sys.argv = ["papa", "compile", "test.papa"]
        main()
        assert (tmp_path / "test_compiled.py").exists()
    finally:
        os.chdir(old_cwd)
