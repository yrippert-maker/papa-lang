"""Pytest fixtures and helpers for PAPA Lang."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.lexer import lex, LexerError
from src.parser import parse, ParseError
from src.interpreter import Interpreter
from src.environment import PapaError, PapaList, PapaMap, Maybe


def run_papa(source: str, filename: str = "<test>") -> Interpreter:
    """Lex, parse, interpret — returns Interpreter with executed state."""
    tokens = lex(source, filename)
    ast = parse(tokens, source)
    interp = Interpreter()
    interp.interpret(ast, filename)
    return interp


def parse_only(source: str):
    """Lex and parse only — returns AST."""
    tokens = lex(source, "<test>")
    return parse(tokens, source)


def lex_only(source: str):
    """Lex only — returns tokens."""
    return lex(source, "<test>")
