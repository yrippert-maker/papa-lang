"""
PAPA Lang Lexer — Tokenizer
Single string type, indent-based blocks, no semicolons, no brackets for blocks.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional


class TokenType(Enum):
    # Literals
    INT = auto()
    FLOAT = auto()
    TEXT = auto()
    BOOL = auto()

    # Identifiers & Keywords
    IDENT = auto()
    
    # Keywords
    MUT = auto()
    IF = auto()
    ELSE = auto()
    MATCH = auto()
    SOME = auto()
    NONE = auto()
    FOR = auto()
    IN = auto()
    LOOP = auto()
    BREAK = auto()
    RETURN = auto()
    FAIL = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    IS = auto()
    AS = auto()
    TRUE = auto()
    FALSE = auto()
    TYPE = auto()
    MODEL = auto()
    ROUTE = auto()
    SERVE = auto()
    ON = auto()
    PORT = auto()
    TEST = auto()
    ASSERT = auto()
    SAY = auto()
    LOG = auto()
    FN = auto()          # function declaration (optional keyword)
    DO = auto()
    INPUT = auto()
    AUTH = auto()
    REQUIRED = auto()
    GUARD = auto()
    EXISTS = auto()
    ELSE_KW = auto()     # 'else' in guard context
    ASYNC = auto()
    TASK = auto()
    EVERY = auto()
    WHEN = auto()
    ENUM = auto()
    IMPORT = auto()
    FROM = auto()
    MAYBE = auto()
    LIST = auto()
    MAP = auto()
    SET_KW = auto()
    SECRET = auto()
    SENSITIVE = auto()
    HAS = auto()
    MANY = auto()
    UNIQUE = auto()
    WHERE = auto()
    ORDER = auto()
    BY = auto()
    LIMIT = auto()
    REPEAT = auto()
    TIMES = auto()
    WAIT = auto()

    # Time units
    SECONDS = auto()
    MINUTES = auto()
    HOURS = auto()
    DAYS = auto()

    # Operators
    ASSIGN = auto()      # =
    EQ = auto()          # ==
    NEQ = auto()         # !=
    LT = auto()          # <
    GT = auto()          # >
    LTE = auto()         # <=
    GTE = auto()         # >=
    PLUS = auto()        # +
    MINUS = auto()       # -
    STAR = auto()        # *
    SLASH = auto()       # /
    PERCENT = auto()     # %
    ARROW = auto()       # ->
    FAT_ARROW = auto()   # =>
    QUESTION = auto()    # ?
    BANG = auto()        # !
    DOTDOT = auto()      # ..
    DOT = auto()         # .
    QMARK_DOT = auto()   # ?.
    DOUBLE_Q = auto()    # ??
    PIPE = auto()        # |
    AMPERSAND = auto()   # &
    COLON = auto()       # :
    COMMA = auto()       # ,
    AT = auto()          # @
    HASH = auto()        # #

    # Delimiters
    LPAREN = auto()      # (
    RPAREN = auto()      # )
    LBRACKET = auto()    # [
    RBRACKET = auto()    # ]
    LBRACE = auto()      # {
    RBRACE = auto()      # }

    # Structure
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()
    EOF = auto()

    # Special
    INTERPOLATION_START = auto()  # { inside string
    INTERPOLATION_END = auto()    # } inside string
    COMMENT = auto()


KEYWORDS = {
    'mut': TokenType.MUT,
    'if': TokenType.IF,
    'else': TokenType.ELSE,
    'match': TokenType.MATCH,
    'some': TokenType.SOME,
    'none': TokenType.NONE,
    'for': TokenType.FOR,
    'in': TokenType.IN,
    'loop': TokenType.LOOP,
    'break': TokenType.BREAK,
    'return': TokenType.RETURN,
    'fail': TokenType.FAIL,
    'and': TokenType.AND,
    'or': TokenType.OR,
    'not': TokenType.NOT,
    'is': TokenType.IS,
    'as': TokenType.AS,
    'true': TokenType.TRUE,
    'false': TokenType.FALSE,
    'type': TokenType.TYPE,
    'model': TokenType.MODEL,
    'route': TokenType.ROUTE,
    'serve': TokenType.SERVE,
    'on': TokenType.ON,
    'port': TokenType.PORT,
    'test': TokenType.TEST,
    'assert': TokenType.ASSERT,
    'say': TokenType.SAY,
    'log': TokenType.LOG,
    'fn': TokenType.FN,
    'do': TokenType.DO,
    'input': TokenType.INPUT,
    'auth': TokenType.AUTH,
    'required': TokenType.REQUIRED,
    'guard': TokenType.GUARD,
    'exists': TokenType.EXISTS,
    'async': TokenType.ASYNC,
    'task': TokenType.TASK,
    'every': TokenType.EVERY,
    'when': TokenType.WHEN,
    'enum': TokenType.ENUM,
    'import': TokenType.IMPORT,
    'from': TokenType.FROM,
    'maybe': TokenType.MAYBE,
    'list': TokenType.LIST,
    'map': TokenType.MAP,
    'set': TokenType.SET_KW,
    'secret': TokenType.SECRET,
    'sensitive': TokenType.SENSITIVE,
    'has': TokenType.HAS,
    'many': TokenType.MANY,
    'unique': TokenType.UNIQUE,
    'where': TokenType.WHERE,
    'order': TokenType.ORDER,
    'by': TokenType.BY,
    'limit': TokenType.LIMIT,
    'repeat': TokenType.REPEAT,
    'times': TokenType.TIMES,
    'wait': TokenType.WAIT,
    'seconds': TokenType.SECONDS,
    'minutes': TokenType.MINUTES,
    'hours': TokenType.HOURS,
    'days': TokenType.DAYS,
}


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    col: int

    def __repr__(self):
        if self.type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
            return f"Token({self.type.name}, L{self.line})"
        return f"Token({self.type.name}, {self.value!r}, L{self.line}:{self.col})"


class LexerError(Exception):
    def __init__(self, message: str, line: int, col: int, source_line: str = ""):
        self.line = line
        self.col = col
        self.source_line = source_line
        super().__init__(self._format(message))

    def _format(self, message: str) -> str:
        lines = [
            f"",
            f"── ОШИБКА ЛЕКСЕРА в строке {self.line} ──────────────",
            f"",
            f"  {self.source_line}" if self.source_line else "",
            f"  {' ' * (self.col - 1)}^^^" if self.source_line else "",
            f"",
            f"  {message}",
            f"",
        ]
        return "\n".join(lines)


class Lexer:
    def __init__(self, source: str, filename: str = "<stdin>"):
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []
        self.indent_stack = [0]
        self.source_lines = source.split('\n')

    def peek(self) -> Optional[str]:
        if self.pos < len(self.source):
            return self.source[self.pos]
        return None

    def advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def peek_ahead(self, n: int = 1) -> Optional[str]:
        pos = self.pos + n
        if pos < len(self.source):
            return self.source[pos]
        return None

    def source_line(self, line_num: int) -> str:
        if 0 < line_num <= len(self.source_lines):
            return self.source_lines[line_num - 1]
        return ""

    def error(self, message: str) -> LexerError:
        return LexerError(message, self.line, self.col, self.source_line(self.line))

    def skip_comment(self):
        """Skip // comments"""
        while self.pos < len(self.source) and self.source[self.pos] != '\n':
            self.pos += 1
            self.col += 1

    def read_string(self) -> Token:
        """Read a string with interpolation support. Only double quotes."""
        start_line = self.line
        start_col = self.col
        self.advance()  # skip opening "

        # Check for triple quotes (multiline)
        if self.peek() == '"' and self.peek_ahead() == '"':
            self.advance()  # skip second "
            self.advance()  # skip third "
            return self.read_multiline_string(start_line, start_col)

        result = []
        while self.pos < len(self.source):
            ch = self.peek()
            if ch == '"':
                self.advance()  # skip closing "
                return Token(TokenType.TEXT, ''.join(result), start_line, start_col)
            elif ch == '{':
                # Interpolation — for now, include as-is in string value
                self.advance()
                expr = []
                depth = 1
                while self.pos < len(self.source) and depth > 0:
                    c = self.peek()
                    if c == '{':
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0:
                            self.advance()
                            break
                    expr.append(self.advance())
                result.append('{')
                result.append(''.join(expr))
                result.append('}')
            elif ch == '\\':
                self.advance()
                esc = self.advance()
                escape_map = {'n': '\n', 't': '\t', '\\': '\\', '"': '"', '{': '{', '}': '}'}
                result.append(escape_map.get(esc, esc))
            elif ch == '\n':
                raise self.error("Строка не закрыта. Используйте тройные кавычки для многострочных строк.")
            else:
                result.append(self.advance())

        raise self.error("Строка не закрыта — пропущена закрывающая кавычка \"")

    def read_multiline_string(self, start_line: int, start_col: int) -> Token:
        """Read triple-quoted multiline string."""
        result = []
        while self.pos < len(self.source):
            if self.peek() == '"' and self.peek_ahead() == '"' and self.peek_ahead(2) == '"':
                self.advance()
                self.advance()
                self.advance()
                text = ''.join(result)
                # Strip leading/trailing newlines
                if text.startswith('\n'):
                    text = text[1:]
                if text.endswith('\n'):
                    text = text[:-1]
                return Token(TokenType.TEXT, text, start_line, start_col)
            else:
                result.append(self.advance())
        raise self.error("Многострочная строка не закрыта — пропущены закрывающие тройные кавычки")

    def read_number(self) -> Token:
        start_col = self.col
        result = []
        is_float = False

        while self.pos < len(self.source):
            ch = self.peek()
            if ch and ch.isdigit():
                result.append(self.advance())
            elif ch == '.' and not is_float:
                if self.peek_ahead() and self.peek_ahead().isdigit():
                    is_float = True
                    result.append(self.advance())
                else:
                    break
            elif ch == '_':  # Allow 1_000_000
                self.advance()
            else:
                break

        value = ''.join(result)
        if is_float:
            return Token(TokenType.FLOAT, value, self.line, start_col)
        return Token(TokenType.INT, value, self.line, start_col)

    def read_identifier(self) -> Token:
        start_col = self.col
        result = []
        while self.pos < len(self.source):
            ch = self.peek()
            if ch and (ch.isalnum() or ch in ('_', '?', '!')):
                result.append(self.advance())
            else:
                break
        value = ''.join(result)

        # Check keywords
        token_type = KEYWORDS.get(value, TokenType.IDENT)
        if value == 'true':
            return Token(TokenType.BOOL, 'true', self.line, start_col)
        elif value == 'false':
            return Token(TokenType.BOOL, 'false', self.line, start_col)
        return Token(token_type, value, self.line, start_col)

    def tokenize(self) -> List[Token]:
        """Main tokenization loop."""
        tokens = []

        while self.pos < len(self.source):
            # Handle start of line — indentation
            if self.col == 1:
                indent = 0
                while self.pos < len(self.source) and self.source[self.pos] == ' ':
                    indent += 1
                    self.pos += 1
                    self.col += 1

                # Skip blank lines
                if self.pos < len(self.source) and self.source[self.pos] == '\n':
                    self.advance()
                    continue

                # Skip comment-only lines
                if self.pos < len(self.source) and self.source[self.pos] == '/' and \
                   self.pos + 1 < len(self.source) and self.source[self.pos + 1] == '/':
                    self.skip_comment()
                    if self.pos < len(self.source):
                        self.advance()  # skip newline
                    continue

                # EOF after spaces
                if self.pos >= len(self.source):
                    break

                current_indent = self.indent_stack[-1]
                if indent > current_indent:
                    self.indent_stack.append(indent)
                    tokens.append(Token(TokenType.INDENT, str(indent), self.line, 1))
                elif indent < current_indent:
                    while self.indent_stack[-1] > indent:
                        self.indent_stack.pop()
                        tokens.append(Token(TokenType.DEDENT, str(indent), self.line, 1))
                    if self.indent_stack[-1] != indent:
                        raise self.error(
                            f"Неверный отступ: {indent} пробелов. "
                            f"Ожидалось {self.indent_stack[-1]}."
                        )

            ch = self.peek()
            if ch is None:
                break

            # Whitespace (not newline, not start of line)
            if ch == ' ' or ch == '\t':
                self.advance()
                continue

            # Newline
            if ch == '\n':
                tokens.append(Token(TokenType.NEWLINE, '\\n', self.line, self.col))
                self.advance()
                continue

            # Comment
            if ch == '/' and self.peek_ahead() == '/':
                self.skip_comment()
                continue

            # String — only double quotes
            if ch == '"':
                tokens.append(self.read_string())
                continue

            # Single quotes — helpful error
            if ch == "'":
                raise self.error(
                    "В PAPA Lang используются только двойные кавычки \"...\"\n"
                    "  Замените ' на \""
                )

            # Backtick — helpful error
            if ch == '`':
                raise self.error(
                    "В PAPA Lang нет обратных кавычек.\n"
                    "  Используйте двойные кавычки: \"текст с {переменной}\""
                )

            # Numbers
            if ch.isdigit():
                tokens.append(self.read_number())
                continue

            # Identifiers and keywords
            if ch.isalpha() or ch == '_':
                tokens.append(self.read_identifier())
                continue

            # Two-character operators
            two_char = self.source[self.pos:self.pos + 2] if self.pos + 1 < len(self.source) else ""
            if two_char == '->':
                tokens.append(Token(TokenType.ARROW, '->', self.line, self.col))
                self.advance(); self.advance()
                continue
            if two_char == '=>':
                tokens.append(Token(TokenType.FAT_ARROW, '=>', self.line, self.col))
                self.advance(); self.advance()
                continue
            if two_char == '==':
                tokens.append(Token(TokenType.EQ, '==', self.line, self.col))
                self.advance(); self.advance()
                continue
            if two_char == '!=':
                tokens.append(Token(TokenType.NEQ, '!=', self.line, self.col))
                self.advance(); self.advance()
                continue
            if two_char == '<=':
                tokens.append(Token(TokenType.LTE, '<=', self.line, self.col))
                self.advance(); self.advance()
                continue
            if two_char == '>=':
                tokens.append(Token(TokenType.GTE, '>=', self.line, self.col))
                self.advance(); self.advance()
                continue
            if two_char == '?.':
                tokens.append(Token(TokenType.QMARK_DOT, '?.', self.line, self.col))
                self.advance(); self.advance()
                continue
            if two_char == '??':
                tokens.append(Token(TokenType.DOUBLE_Q, '??', self.line, self.col))
                self.advance(); self.advance()
                continue
            if two_char == '..':
                tokens.append(Token(TokenType.DOTDOT, '..', self.line, self.col))
                self.advance(); self.advance()
                continue

            # Single-character operators
            single_ops = {
                '=': TokenType.ASSIGN,
                '+': TokenType.PLUS,
                '-': TokenType.MINUS,
                '*': TokenType.STAR,
                '/': TokenType.SLASH,
                '%': TokenType.PERCENT,
                '<': TokenType.LT,
                '>': TokenType.GT,
                '?': TokenType.QUESTION,
                '!': TokenType.BANG,
                '.': TokenType.DOT,
                '|': TokenType.PIPE,
                '&': TokenType.AMPERSAND,
                ':': TokenType.COLON,
                ',': TokenType.COMMA,
                '@': TokenType.AT,
                '#': TokenType.HASH,
                '(': TokenType.LPAREN,
                ')': TokenType.RPAREN,
                '[': TokenType.LBRACKET,
                ']': TokenType.RBRACKET,
                '{': TokenType.LBRACE,
                '}': TokenType.RBRACE,
            }

            if ch in single_ops:
                tokens.append(Token(single_ops[ch], ch, self.line, self.col))
                self.advance()
                continue

            raise self.error(f"Неожиданный символ: '{ch}'")

        # Close remaining indents
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            tokens.append(Token(TokenType.DEDENT, '0', self.line, self.col))

        tokens.append(Token(TokenType.EOF, '', self.line, self.col))
        return tokens


def lex(source: str, filename: str = "<stdin>") -> List[Token]:
    """Convenience function to tokenize source code."""
    return Lexer(source, filename).tokenize()
