"""
PAPA Lang — Programming language of the next generation.
No null. No semicolons. No backtick confusion. One string type.
Built-in safety, readable by humans and AI.
"""

__version__ = "0.2.0"

from .lexer import lex, Lexer
from .parser import parse, Parser
from .interpreter import run, Interpreter
from .ast_nodes import *
