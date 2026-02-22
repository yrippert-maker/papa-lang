"""PAPA Lang Parser tests."""
import pytest
from src.lexer import lex
from src.parser import parse, ParseError
from src.ast_nodes import (
    Program, SayStatement, IntLiteral, BinaryOp,
    IfStatement, ForLoop, FunctionDef, Assignment,
)


def parse_source(source: str):
    tokens = lex(source, "<test>")
    return parse(tokens, source)


class TestExpressions:
    def test_say_with_int(self):
        ast = parse_source("say 42")
        assert len(ast.statements) == 1
        assert isinstance(ast.statements[0], SayStatement)
        assert isinstance(ast.statements[0].expr, IntLiteral)
        assert ast.statements[0].expr.value == 42

    def test_say_with_binary_op(self):
        ast = parse_source("say 1 + 2")
        assert len(ast.statements) == 1
        node = ast.statements[0].expr
        assert isinstance(node, BinaryOp)
        assert node.op == "+"

    def test_say_statement(self):
        ast = parse_source('say "hello"')
        assert len(ast.statements) == 1
        assert isinstance(ast.statements[0], SayStatement)


class TestStatements:
    def test_if_else(self):
        ast = parse_source("if x\n  say 1\nelse\n  say 2")
        assert len(ast.statements) == 1
        assert isinstance(ast.statements[0], IfStatement)

    def test_for_loop(self):
        ast = parse_source("for i in range(10)\n  say i")
        assert len(ast.statements) == 1
        assert isinstance(ast.statements[0], ForLoop)


class TestDefinitions:
    def test_function_short(self):
        ast = parse_source("double(x) -> int = x * 2")
        assert len(ast.statements) == 1
        assert isinstance(ast.statements[0], FunctionDef)
        assert ast.statements[0].name == "double"
        assert ast.statements[0].return_type == "int"

    def test_assignment(self):
        ast = parse_source("x = 42")
        assert len(ast.statements) == 1
        assert isinstance(ast.statements[0], Assignment)
        assert ast.statements[0].name == "x"


class TestErrorRecovery:
    def test_multiple_errors_collected(self):
        source = 'say "ok"\nelse\nsay "b"\nmatch x\nsay "c"'
        with pytest.raises(ParseError) as exc_info:
            parse_source(source)
        assert "Найдено" in str(exc_info.value)
        assert "2" in str(exc_info.value) or "ошибок" in str(exc_info.value)
