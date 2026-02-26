"""Tokenizer for .papa DSL — pure Python, no external deps."""

import re
from typing import List

KEYWORD = "KEYWORD"
IDENT = "IDENT"
STRING = "STRING"
NUMBER = "NUMBER"
FRACTION = "FRACTION"
LBRACE = "LBRACE"
RBRACE = "RBRACE"
LBRACKET = "LBRACKET"
RBRACKET = "RBRACKET"
COLON = "COLON"
COMMA = "COMMA"
EOF = "EOF"

KEYWORDS = frozenset({"agent", "swarm", "tool", "pipeline", "import"})


class Token:
    def __init__(self, type: str, value: object, line: int, col: int):
        self.type = type
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self):
        return f"Token({self.type!r}, {self.value!r}, {self.line}:{self.col})"


class LexError(Exception):
    def __init__(self, message: str, line: int, col: int):
        super().__init__(f"Lexer error at line {line}, col {col}: {message}")
        self.line = line
        self.col = col


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1

    def _peek(self) -> str:
        if self.pos >= len(self.source):
            return "\0"
        return self.source[self.pos]

    def _advance(self) -> str:
        if self.pos >= len(self.source):
            return "\0"
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _skip_whitespace(self) -> None:
        while self.pos < len(self.source):
            ch = self._peek()
            if ch in " \t\n\r":
                self._advance()
            elif ch == "/" and self._peek_2() == "/":
                self._skip_comment()
            else:
                break

    def _peek_2(self) -> str:
        if self.pos + 1 >= len(self.source):
            return "\0"
        return self.source[self.pos + 1]

    def _skip_comment(self) -> None:
        while self.pos < len(self.source) and self._peek() != "\n":
            self._advance()

    def tokenize(self) -> List[Token]:
        tokens = []
        self._skip_whitespace()

        while self.pos < len(self.source):
            start_line, start_col = self.line, self.col
            ch = self._peek()

            if ch in " \t\n\r":
                self._skip_whitespace()
                continue

            if ch == "{":
                self._advance()
                tokens.append(Token(LBRACE, "{", start_line, start_col))
            elif ch == "}":
                self._advance()
                tokens.append(Token(RBRACE, "}", start_line, start_col))
            elif ch == "[":
                self._advance()
                tokens.append(Token(LBRACKET, "[", start_line, start_col))
            elif ch == "]":
                self._advance()
                tokens.append(Token(RBRACKET, "]", start_line, start_col))
            elif ch == ":":
                self._advance()
                tokens.append(Token(COLON, ":", start_line, start_col))
            elif ch == ",":
                self._advance()
                tokens.append(Token(COMMA, ",", start_line, start_col))
            elif ch in "'\"":
                quote = ch
                self._advance()
                buf = []
                while self.pos < len(self.source) and self._peek() != quote:
                    buf.append(self._advance())
                if self._peek() != quote:
                    raise LexError("Unterminated string", self.line, self.col)
                self._advance()
                tokens.append(Token(STRING, "".join(buf), start_line, start_col))
            elif ch.isdigit():
                buf = []
                while self._peek().isdigit():
                    buf.append(self._advance())
                if self._peek() == "/" and self.pos < len(self.source) - 1 and self.source[self.pos + 1].isdigit():
                    num1 = int("".join(buf))
                    self._advance()
                    buf2 = []
                    while self._peek().isdigit():
                        buf2.append(self._advance())
                    num2 = int("".join(buf2))
                    tokens.append(Token(FRACTION, (num1, num2), start_line, start_col))
                elif self._peek() == "." and self.pos < len(self.source) - 1 and self.source[self.pos + 1].isdigit():
                    buf.append(self._advance())
                    while self._peek().isdigit():
                        buf.append(self._advance())
                    tokens.append(Token(NUMBER, float("".join(buf)), start_line, start_col))
                else:
                    tokens.append(Token(NUMBER, int("".join(buf)), start_line, start_col))
            elif ch.isalpha() or ch == "_" or ch == "-":
                buf = []
                while self._peek().isalnum() or self._peek() in "_-.":
                    buf.append(self._advance())
                s = "".join(buf)
                if s.lower() in KEYWORDS:
                    tokens.append(Token(KEYWORD, s.lower(), start_line, start_col))
                else:
                    tokens.append(Token(IDENT, s, start_line, start_col))
            else:
                raise LexError(f"Unexpected character {ch!r}", start_line, start_col)

            self._skip_whitespace()

        tokens.append(Token(EOF, "", self.line, self.col))
        return tokens
