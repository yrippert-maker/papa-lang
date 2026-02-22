"""PAPA Lang Lexer tests."""
import pytest
from src.lexer import lex, LexerError


class TestNumbers:
    def test_int_literal(self):
        tokens = lex("42", "<test>")
        assert len(tokens) >= 1
        assert tokens[0].type.name == "INT"
        assert tokens[0].value == "42"

    def test_float_literal(self):
        tokens = lex("3.14", "<test>")
        assert tokens[0].type.name == "FLOAT"
        assert tokens[0].value == "3.14"

    def test_int_with_underscores(self):
        tokens = lex("1_000_000", "<test>")
        assert tokens[0].type.name == "INT"
        assert "1000000" in tokens[0].value or tokens[0].value == "1_000_000"


class TestStrings:
    def test_simple_string(self):
        tokens = lex('"hello"', "<test>")
        assert tokens[0].type.name == "TEXT"
        assert "hello" in tokens[0].value

    def test_string_with_escape(self):
        tokens = lex(r'"hello\nworld"', "<test>")
        assert tokens[0].type.name == "TEXT"

    def test_string_interpolation(self):
        tokens = lex('"hello {x}"', "<test>")
        # Should tokenize (interpolation is handled in parser)
        assert any(t.type.name == "TEXT" for t in tokens)


class TestOperators:
    def test_eq_ne(self):
        tokens = lex("== !=", "<test>")
        types = [t.type.name for t in tokens]
        assert "EQ" in types
        assert "NEQ" in types

    def test_optional_chain(self):
        tokens = lex("?. ??", "<test>")
        types = [t.type.name for t in tokens]
        assert "QMARK_DOT" in types
        assert "DOUBLE_Q" in types

    def test_arrow(self):
        tokens = lex("=> ->", "<test>")
        types = [t.type.name for t in tokens]
        assert "FAT_ARROW" in types
        assert "ARROW" in types


class TestKeywords:
    def test_if_else_for(self):
        tokens = lex("if else for", "<test>")
        types = [t.type.name for t in tokens]
        assert "IF" in types
        assert "ELSE" in types
        assert "FOR" in types

    def test_mut_model_route_test(self):
        tokens = lex("mut model route test", "<test>")
        types = [t.type.name for t in tokens]
        assert "MUT" in types
        assert "MODEL" in types
        assert "ROUTE" in types
        assert "TEST" in types

    def test_import(self):
        tokens = lex('import "std/math"', "<test>")
        assert any(t.type.name == "IMPORT" for t in tokens)


class TestIndent:
    def test_indent_dedent(self):
        source = 'say "a"\n  say "b"\nsay "c"'
        tokens = lex(source, "<test>")
        types = [t.type.name for t in tokens]
        assert "INDENT" in types
        assert "DEDENT" in types
