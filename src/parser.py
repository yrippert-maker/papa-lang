"""
PAPA Lang Parser — Token stream to AST
"""

from typing import List, Optional, Any
from .lexer import Token, TokenType, LexerError
from .ast_nodes import *


class ParseError(Exception):
    def __init__(self, message: str, token: Token, source_lines: List[str] = None):
        self.token = token
        line_text = ""
        if source_lines and 0 < token.line <= len(source_lines):
            line_text = source_lines[token.line - 1]
        formatted = self._format(message, token, line_text)
        super().__init__(formatted)

    def _format(self, message: str, token: Token, line_text: str) -> str:
        lines = [
            f"",
            f"── ОШИБКА ПАРСЕРА в строке {token.line} ──────────────",
            f"",
        ]
        if line_text:
            lines.append(f"  {line_text}")
            lines.append(f"  {' ' * max(0, token.col - 1)}^^^")
        lines.extend([
            f"",
            f"  {message}",
            f"",
        ])
        return "\n".join(lines)


class Parser:
    def __init__(self, tokens: List[Token], source: str = ""):
        self.tokens = tokens
        self.pos = 0
        self.source_lines = source.split('\n') if source else []
        self.errors: List[ParseError] = []
        self.max_errors = 20

    def peek(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, '', 0, 0)

    def peek_ahead_type(self, n: int = 1) -> TokenType:
        pos = self.pos + n
        if pos < len(self.tokens):
            return self.tokens[pos].type
        return TokenType.EOF

    def advance(self) -> Token:
        token = self.peek()
        self.pos += 1
        return token

    def expect(self, token_type: TokenType, message: str = "") -> Token:
        token = self.peek()
        if token.type != token_type:
            msg = message or f"Ожидалось {token_type.name}, получено {token.type.name} ({token.value!r})"
            raise ParseError(msg, token, self.source_lines)
        return self.advance()

    def match(self, *types: TokenType) -> Optional[Token]:
        if self.peek().type in types:
            return self.advance()
        return None

    TYPE_TOKEN_NAMES = {
        TokenType.MAYBE: "maybe",
        TokenType.LIST: "list",
        TokenType.MAP: "map",
        TokenType.SECRET: "secret",
    }

    def _parse_type_name(self) -> str:
        """Parse type identifier: IDENT or maybe/list/map/secret keyword."""
        t = self.peek()
        if t.type == TokenType.IDENT:
            return self.advance().value
        if t.type in self.TYPE_TOKEN_NAMES:
            self.advance()
            return self.TYPE_TOKEN_NAMES[t.type]
        raise ParseError(f"Ожидалось имя типа, получено {t.type.name}", t, self.source_lines)

    def skip_newlines(self):
        while self.peek().type == TokenType.NEWLINE:
            self.advance()

    def error(self, message: str) -> ParseError:
        return ParseError(message, self.peek(), self.source_lines)

    def record_error(self, message: str = "") -> None:
        """Record parse error and optionally raise if limit reached."""
        token = self.peek()
        msg = message or f"Неожиданный токен: {token.type.name} ({token.value!r})"
        err = ParseError(msg, token, self.source_lines)
        self.errors.append(err)
        if len(self.errors) >= self.max_errors:
            raise self._raise_all_errors()

    def synchronize(self) -> None:
        """Skip tokens until next statement boundary."""
        while self.peek().type not in (
            TokenType.EOF,
            TokenType.NEWLINE,
            TokenType.DEDENT,
        ):
            self.advance()
        self.skip_newlines()

    def _raise_all_errors(self) -> None:
        """Build and raise single error with all collected messages."""
        lines = [f"Найдено {len(self.errors)} ошибок парсинга:"]
        for i, err in enumerate(self.errors[:10], 1):
            lines.append(f"  {i}. Строка {err.token.line}: {err.token.value!r} — {str(err).strip()}")
        if len(self.errors) > 10:
            lines.append(f"  ... и ещё {len(self.errors) - 10} ошибок")
        msg = "\n".join(lines)
        raise ParseError(msg, self.peek(), self.source_lines)

    # ── Main parse ──

    def parse(self) -> Program:
        self.errors = []
        self.skip_newlines()
        stmts = []
        while self.peek().type != TokenType.EOF:
            try:
                stmt = self.parse_statement()
                if stmt:
                    stmts.append(stmt)
            except ParseError as e:
                self.errors.append(e)
                if len(self.errors) >= self.max_errors:
                    self._raise_all_errors()
                self.synchronize()
                continue
            self.skip_newlines()
        if self.errors:
            raise self._raise_all_errors()
        return Program(statements=stmts)

    # ── Statements ──

    def parse_statement(self) -> Any:
        token = self.peek()

        if token.type == TokenType.SAY:
            return self.parse_say()
        elif token.type == TokenType.LOG:
            return self.parse_log()
        elif token.type == TokenType.MUT:
            return self.parse_mutable_assignment()
        elif token.type == TokenType.IF:
            return self.parse_if()
        elif token.type == TokenType.MATCH:
            return self.parse_match()
        elif token.type == TokenType.FOR:
            return self.parse_for()
        elif token.type == TokenType.LOOP:
            return self.parse_loop()
        elif token.type == TokenType.REPEAT:
            return self.parse_repeat()
        elif token.type == TokenType.RETURN:
            return self.parse_return()
        elif token.type == TokenType.FAIL:
            return self.parse_fail()
        elif token.type == TokenType.BREAK:
            self.advance()
            self.skip_newlines()
            return BreakStatement(line=token.line, col=token.col)
        elif token.type == TokenType.WAIT:
            return self.parse_wait()
        elif token.type == TokenType.ASSERT:
            return self.parse_assert()
        elif token.type == TokenType.TYPE:
            return self.parse_type_def()
        elif token.type == TokenType.SERVE:
            return self.parse_serve()
        elif token.type == TokenType.ROUTE:
            return self.parse_route()
        elif token.type == TokenType.TEST:
            return self.parse_test()
        elif token.type == TokenType.IMPORT:
            return self.parse_import()
        elif token.type == TokenType.FROM:
            return self.parse_from_import()
        elif token.type == TokenType.TASK:
            return self.parse_task()
        elif token.type == TokenType.EVERY:
            return self.parse_every()
        elif token.type == TokenType.ASYNC:
            return self.parse_async_function_def()
        elif token.type == TokenType.MODEL:
            return self.parse_model()
        elif token.type == TokenType.ENUM:
            return self.parse_enum()
        elif token.type == TokenType.IDENT:
            return self.parse_ident_statement()
        elif token.type in (TokenType.NEWLINE, TokenType.DEDENT):
            self.advance()
            return None
        else:
            # Try parsing as expression
            expr = self.parse_expression()
            self.skip_newlines()
            return expr

    def parse_say(self) -> SayStatement:
        token = self.advance()  # consume 'say'
        expr = self.parse_expression()
        self.skip_newlines()
        return SayStatement(expr=expr, line=token.line, col=token.col)

    def parse_log(self) -> LogStatement:
        token = self.advance()  # consume 'log'
        # Check for level: log.info, log.warn, log.error
        level = "info"
        if self.peek().type == TokenType.DOT:
            self.advance()
            level_token = self.expect(TokenType.IDENT)
            level = level_token.value
        expr = self.parse_expression()
        self.skip_newlines()
        return LogStatement(level=level, expr=expr, line=token.line, col=token.col)

    def parse_mutable_assignment(self) -> Assignment:
        self.advance()  # consume 'mut'
        name_token = self.expect(TokenType.IDENT, "Ожидалось имя переменной после 'mut'")

        type_ann = None
        if self.match(TokenType.COLON):
            type_ann = self._parse_type_name()

        self.expect(TokenType.ASSIGN, "Ожидалось '=' после имени переменной")
        value = self.parse_expression()
        self.skip_newlines()
        return Assignment(
            name=name_token.value, value=value, mutable=True,
            type_annotation=type_ann,
            line=name_token.line, col=name_token.col
        )

    def parse_ident_statement(self) -> Any:
        """Parse identifier-starting statements (assignment, reassignment, function call, function def)."""
        name_token = self.advance()
        name = name_token.value

        # Function definition: name(params) -> type
        if self.peek().type == TokenType.LPAREN and self._is_func_def():
            return self.parse_function_def(name_token)

        # Assignment: name = value
        if self.peek().type == TokenType.ASSIGN:
            self.advance()
            value = self.parse_expression()
            self.skip_newlines()
            return Assignment(
                name=name, value=value, mutable=False,
                line=name_token.line, col=name_token.col
            )

        # Assignment with type: name : type = value
        if self.peek().type == TokenType.COLON:
            self.advance()
            type_ann = self._parse_type_name()
            self.expect(TokenType.ASSIGN)
            value = self.parse_expression()
            self.skip_newlines()
            return Assignment(
                name=name, value=value, mutable=False,
                type_annotation=type_ann,
                line=name_token.line, col=name_token.col
            )

        # Otherwise — backtrack and parse as expression
        self.pos -= 1
        expr = self.parse_expression()
        
        # Check for reassignment: expr = value
        if self.peek().type == TokenType.ASSIGN:
            self.advance()
            value = self.parse_expression()
            self.skip_newlines()
            return Reassignment(target=expr, value=value, line=name_token.line, col=name_token.col)

        self.skip_newlines()
        return expr

    def _is_func_def(self) -> bool:
        """Lookahead to check if this is a function definition."""
        save_pos = self.pos
        try:
            depth = 0
            while self.pos < len(self.tokens):
                t = self.tokens[self.pos]
                if t.type == TokenType.LPAREN:
                    depth += 1
                elif t.type == TokenType.RPAREN:
                    depth -= 1
                    if depth == 0:
                        self.pos += 1
                        # Check for -> (return type) or NEWLINE+INDENT (body)
                        while self.pos < len(self.tokens) and self.tokens[self.pos].type == TokenType.NEWLINE:
                            self.pos += 1
                        if self.pos < len(self.tokens):
                            next_t = self.tokens[self.pos]
                            return next_t.type in (TokenType.ARROW, TokenType.INDENT, TokenType.NEWLINE, TokenType.ASSIGN)
                        return False
                elif t.type in (TokenType.NEWLINE, TokenType.EOF):
                    return False
                self.pos += 1
            return False
        finally:
            self.pos = save_pos

    def parse_function_def(self, name_token: Token) -> FunctionDef:
        name = name_token.value
        can_fail = name.endswith('!')
        if can_fail:
            name = name[:-1]

        # Parse params
        self.expect(TokenType.LPAREN)
        params = []
        while self.peek().type != TokenType.RPAREN:
            pname = self.expect(TokenType.IDENT).value
            ptype = None
            pdefault = None
            if self.match(TokenType.COLON):
                ptype = self._parse_type_name()
            if self.match(TokenType.ASSIGN):
                pdefault = self.parse_expression()
            params.append((pname, ptype, pdefault))
            self.match(TokenType.COMMA)
        self.expect(TokenType.RPAREN)

        # Return type (IDENT or type keywords: maybe, list, map, secret)
        return_type = None
        if self.match(TokenType.ARROW):
            return_type = self._parse_type_name()

        # Short form: name(x) -> type = expr
        if self.match(TokenType.ASSIGN):
            expr = self.parse_expression()
            self.skip_newlines()
            return FunctionDef(
                name=name, params=params, return_type=return_type,
                can_fail=can_fail, body=[ReturnStatement(value=expr)],
                line=name_token.line, col=name_token.col
            )

        # Block body
        self.skip_newlines()
        body = self.parse_block()
        return FunctionDef(
            name=name, params=params, return_type=return_type,
            can_fail=can_fail, body=body,
            line=name_token.line, col=name_token.col
        )

    def parse_if(self) -> IfStatement:
        token = self.advance()  # consume 'if'
        condition = self.parse_expression()
        self.skip_newlines()
        body = self.parse_block()

        elif_branches = []
        else_body = []

        while True:
            self.skip_newlines()
            if self.peek().type == TokenType.ELSE:
                self.advance()
                if self.peek().type == TokenType.IF:
                    self.advance()
                    elif_cond = self.parse_expression()
                    self.skip_newlines()
                    elif_body = self.parse_block()
                    elif_branches.append((elif_cond, elif_body))
                else:
                    self.skip_newlines()
                    else_body = self.parse_block()
                    break
            else:
                break

        return IfStatement(
            condition=condition, body=body,
            elif_branches=elif_branches, else_body=else_body,
            line=token.line, col=token.col
        )

    def parse_match(self) -> MatchStatement:
        token = self.advance()  # consume 'match'
        expr = self.parse_expression()
        self.skip_newlines()
        self.expect(TokenType.INDENT)

        arms = []
        while self.peek().type != TokenType.DEDENT and self.peek().type != TokenType.EOF:
            self.skip_newlines()
            if self.peek().type == TokenType.DEDENT:
                break
            # Wildcard
            if self.peek().type == TokenType.IDENT and self.peek().value == '_':
                self.advance()
                pattern = Identifier(name='_', line=token.line, col=token.col)
            else:
                pattern = self.parse_expression()
            self.expect(TokenType.ARROW, "Ожидалось '->' после паттерна в match")
            # Поддержка блоков И однострочных выражений
            self.skip_newlines()
            if self.peek().type == TokenType.INDENT:
                body = self.parse_block()
            else:
                stmt = self.parse_statement()
                body = [stmt] if stmt else []
            arms.append((pattern, body))
            self.skip_newlines()

        self.match(TokenType.DEDENT)
        return MatchStatement(expr=expr, arms=arms, line=token.line, col=token.col)

    def parse_for(self) -> ForLoop:
        token = self.advance()  # consume 'for'
        var = self.expect(TokenType.IDENT).value
        index_var = None
        # Поддержка: for i, item in list
        if self.peek().type == TokenType.COMMA:
            self.advance()  # consume ','
            index_var = var
            var = self.expect(TokenType.IDENT).value
        self.expect(TokenType.IN, "Ожидалось 'in' в цикле for")
        iterable = self.parse_expression()
        self.skip_newlines()
        body = self.parse_block()
        node = ForLoop(var=var, iterable=iterable, body=body, line=token.line, col=token.col)
        node.index_var = index_var
        return node

    def parse_enum(self):
        token = self.advance()  # consume 'enum'
        name = self.expect(TokenType.IDENT).value
        self.skip_newlines()
        self.expect(TokenType.INDENT)
        variants = []
        while self.peek().type != TokenType.DEDENT and self.peek().type != TokenType.EOF:
            self.skip_newlines()
            if self.peek().type == TokenType.DEDENT:
                break
            variant = self.expect(TokenType.IDENT).value
            variants.append(variant)
            self.skip_newlines()
        self.match(TokenType.DEDENT)
        return EnumDef(name=name, variants=variants, line=token.line, col=token.col)

    def parse_loop(self) -> LoopStatement:
        token = self.advance()  # consume 'loop'
        self.skip_newlines()
        body = self.parse_block()
        return LoopStatement(body=body, line=token.line, col=token.col)

    def parse_repeat(self) -> RepeatStatement:
        token = self.advance()  # consume 'repeat'
        count = self.parse_expression()
        self.expect(TokenType.TIMES)
        self.skip_newlines()
        body = self.parse_block()
        else_body = []
        if self.peek().type == TokenType.ELSE:
            self.advance()
            self.skip_newlines()
            else_body = self.parse_block()
        return RepeatStatement(count=count, body=body, else_body=else_body,
                               line=token.line, col=token.col)

    def parse_return(self) -> ReturnStatement:
        token = self.advance()
        value = None
        if self.peek().type not in (TokenType.NEWLINE, TokenType.DEDENT, TokenType.EOF):
            value = self.parse_expression()
        self.skip_newlines()
        return ReturnStatement(value=value, line=token.line, col=token.col)

    def parse_fail(self) -> FailStatement:
        token = self.advance()
        message = self.parse_expression()
        self.skip_newlines()
        return FailStatement(message=message, line=token.line, col=token.col)

    def parse_wait(self) -> WaitStatement:
        token = self.advance()  # consume 'wait'
        duration = self.parse_expression()
        unit = "seconds"
        if self.peek().type in (TokenType.SECONDS, TokenType.MINUTES, TokenType.HOURS, TokenType.DAYS):
            unit = self.advance().value
        self.skip_newlines()
        return WaitStatement(duration=duration, unit=unit, line=token.line, col=token.col)

    def parse_assert(self) -> AssertStatement:
        token = self.advance()
        expr = self.parse_expression()
        self.skip_newlines()
        return AssertStatement(expr=expr, line=token.line, col=token.col)

    def parse_type_def(self) -> TypeDef:
        self.advance()  # consume 'type'
        name = self.expect(TokenType.IDENT).value
        self.skip_newlines()

        fields = []
        variants = []

        if self.peek().type == TokenType.INDENT:
            self.advance()
            while self.peek().type != TokenType.DEDENT and self.peek().type != TokenType.EOF:
                self.skip_newlines()
                if self.peek().type == TokenType.DEDENT:
                    break
                field_name = self.expect(TokenType.IDENT).value
                if self.match(TokenType.COLON):
                    field_type = self.expect(TokenType.IDENT).value
                    default = None
                    if self.match(TokenType.ASSIGN):
                        default = self.parse_expression()
                    fields.append((field_name, field_type, default, []))
                elif self.match(TokenType.LPAREN):
                    # Variant with data
                    vfields = []
                    while self.peek().type != TokenType.RPAREN:
                        vf = self.expect(TokenType.IDENT).value
                        vt = None
                        if self.match(TokenType.COLON):
                            vt = self.expect(TokenType.IDENT).value
                        vfields.append((vf, vt))
                        self.match(TokenType.COMMA)
                    self.expect(TokenType.RPAREN)
                    variants.append((field_name, vfields))
                else:
                    # Simple variant
                    variants.append((field_name, []))
                self.skip_newlines()
            self.match(TokenType.DEDENT)

        return TypeDef(name=name, fields=fields, variants=variants)

    def parse_serve(self) -> ServeDef:
        token = self.advance()  # consume 'serve'
        options = {}

        # serve on port 8200
        if self.match(TokenType.ON):
            self.expect(TokenType.PORT)
            port_token = self.expect(TokenType.INT)
            return ServeDef(port=int(port_token.value), line=token.line, col=token.col)

        # Block form
        self.skip_newlines()
        if self.peek().type == TokenType.INDENT:
            self.advance()
            while self.peek().type != TokenType.DEDENT and self.peek().type != TokenType.EOF:
                self.skip_newlines()
                if self.peek().type == TokenType.DEDENT:
                    break
                key = self.expect(TokenType.IDENT).value
                value = self.parse_expression()
                options[key] = value
                self.skip_newlines()
            self.match(TokenType.DEDENT)

        port = 8200
        if 'port' in options and isinstance(options['port'], IntLiteral):
            port = options['port'].value

        return ServeDef(port=port, options=options, line=token.line, col=token.col)

    def parse_route(self) -> RouteDef:
        token = self.advance()  # consume 'route'
        method = self.expect(TokenType.IDENT).value.upper()
        path = self.parse_expression()
        if isinstance(path, TextLiteral):
            path_str = path.value
        elif isinstance(path, BinaryOp) and path.op == '/':
            path_str = '/' + self._extract_path(path)
        else:
            path_str = str(path)

        self.skip_newlines()
        auth_required = False
        input_fields = []
        body = []

        if self.peek().type == TokenType.INDENT:
            self.advance()
            while self.peek().type != TokenType.DEDENT and self.peek().type != TokenType.EOF:
                self.skip_newlines()
                if self.peek().type == TokenType.DEDENT:
                    break
                if self.peek().type == TokenType.AUTH:
                    self.advance()
                    self.expect(TokenType.REQUIRED)
                    auth_required = True
                elif self.peek().type == TokenType.DO:
                    self.advance()
                    self.skip_newlines()
                    body = self.parse_block()
                else:
                    stmt = self.parse_statement()
                    if stmt:
                        body.append(stmt)
                self.skip_newlines()
            self.match(TokenType.DEDENT)

        return RouteDef(method=method, path=path_str, auth_required=auth_required,
                        input_fields=input_fields, body=body,
                        line=token.line, col=token.col)

    def _extract_path(self, node) -> str:
        if isinstance(node, Identifier):
            return node.name
        if isinstance(node, BinaryOp) and node.op == '/':
            return self._extract_path(node.left) + '/' + self._extract_path(node.right)
        return str(node)

    def parse_test(self) -> TestDef:
        token = self.advance()  # consume 'test'
        name = self.expect(TokenType.TEXT).value
        self.skip_newlines()
        body = self.parse_block()
        return TestDef(name=name, body=body, line=token.line, col=token.col)

    def parse_import(self) -> 'ImportStatement':
        token = self.advance()  # consume 'import'
        path_token = self.expect(TokenType.TEXT, "Ожидался путь к файлу в кавычках")
        self.skip_newlines()
        return ImportStatement(path=path_token.value, line=token.line, col=token.col)

    def parse_from_import(self) -> 'FromImportStatement':
        token = self.advance()  # consume 'from'
        path_token = self.expect(TokenType.TEXT, "Ожидался путь к файлу в кавычках")
        self.expect(TokenType.IMPORT, "Ожидалось 'import'")
        names = []
        while True:
            name_tok = self.expect(TokenType.IDENT, "Ожидалось имя для импорта")
            names.append(name_tok.value)
            if not self.match(TokenType.COMMA):
                break
        self.skip_newlines()
        return FromImportStatement(path=path_token.value, names=names, line=token.line, col=token.col)

    def parse_task(self) -> 'TaskDef':
        token = self.advance()  # consume 'task'
        name = self.expect(TokenType.IDENT).value
        self.skip_newlines()
        body = self.parse_block()
        return TaskDef(name=name, body=body, line=token.line, col=token.col)

    def parse_every(self) -> 'EveryDef':
        token = self.advance()  # consume 'every'
        interval = self.parse_expression()
        unit = "seconds"
        if self.peek().type in (TokenType.SECONDS, TokenType.MINUTES, TokenType.HOURS, TokenType.DAYS):
            unit = self.advance().value
        self.skip_newlines()
        body = self.parse_block()
        return EveryDef(interval=interval, unit=unit, body=body, line=token.line, col=token.col)

    def parse_async_function_def(self) -> FunctionDef:
        self.advance()  # consume 'async'
        name_token = self.expect(TokenType.IDENT, "Ожидалось имя функции после 'async'")
        func = self.parse_function_def(name_token)
        func.is_async = True
        return func

    def parse_model(self) -> ModelDef:
        token = self.advance()  # consume 'model'
        name = self.expect(TokenType.IDENT).value
        self.skip_newlines()
        fields = []
        if self.peek().type == TokenType.INDENT:
            self.advance()
            while self.peek().type != TokenType.DEDENT and self.peek().type != TokenType.EOF:
                self.skip_newlines()
                if self.peek().type == TokenType.DEDENT:
                    break
                field_name = self.expect(TokenType.IDENT).value
                self.expect(TokenType.COLON)
                field_type = self.expect(TokenType.IDENT).value
                modifiers = []
                while self.peek().type == TokenType.UNIQUE:
                    self.advance()
                    modifiers.append('unique')
                fields.append((field_name, field_type, modifiers))
                self.skip_newlines()
            self.match(TokenType.DEDENT)
        return ModelDef(name=name, fields=fields, line=token.line, col=token.col)

    def parse_block(self) -> List[Any]:
        """Parse an indented block of statements."""
        stmts = []
        if self.peek().type != TokenType.INDENT:
            # Single-line block
            stmt = self.parse_statement()
            if stmt:
                stmts.append(stmt)
            return stmts

        self.advance()  # consume INDENT
        while self.peek().type != TokenType.DEDENT and self.peek().type != TokenType.EOF:
            self.skip_newlines()
            if self.peek().type == TokenType.DEDENT:
                break
            stmt = self.parse_statement()
            if stmt:
                stmts.append(stmt)
        self.match(TokenType.DEDENT)
        return stmts

    # ── Expressions ──

    def parse_expression(self) -> Any:
        return self.parse_null_coalesce()

    def parse_null_coalesce(self) -> Any:
        left = self.parse_or()
        while self.match(TokenType.DOUBLE_Q):
            right = self.parse_or()
            left = NullCoalesce(expr=left, default=right)
        return left

    def parse_or(self) -> Any:
        left = self.parse_and()
        while self.peek().type == TokenType.OR:
            op = self.advance().value
            right = self.parse_and()
            left = BinaryOp(left=left, op=op, right=right)
        return left

    def parse_and(self) -> Any:
        left = self.parse_not()
        while self.peek().type == TokenType.AND:
            op = self.advance().value
            right = self.parse_not()
            left = BinaryOp(left=left, op=op, right=right)
        return left

    def parse_not(self) -> Any:
        if self.peek().type == TokenType.NOT:
            op_token = self.advance()
            operand = self.parse_not()
            return UnaryOp(op='not', operand=operand, line=op_token.line, col=op_token.col)
        return self.parse_comparison()

    def parse_comparison(self) -> Any:
        left = self.parse_range()
        comp_ops = (TokenType.EQ, TokenType.NEQ, TokenType.LT, TokenType.GT,
                    TokenType.LTE, TokenType.GTE, TokenType.IS)
        while self.peek().type in comp_ops:
            op = self.advance().value
            right = self.parse_range()
            left = BinaryOp(left=left, op=op, right=right)
        return left

    def parse_range(self) -> Any:
        left = self.parse_addition()
        if self.match(TokenType.DOTDOT):
            right = self.parse_addition()
            return RangeLiteral(start=left, end=right)
        return left

    def parse_addition(self) -> Any:
        left = self.parse_multiplication()
        while self.peek().type in (TokenType.PLUS, TokenType.MINUS):
            op = self.advance().value
            right = self.parse_multiplication()
            left = BinaryOp(left=left, op=op, right=right)
        return left

    def parse_multiplication(self) -> Any:
        left = self.parse_unary()
        while self.peek().type in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self.advance().value
            right = self.parse_unary()
            left = BinaryOp(left=left, op=op, right=right)
        return left

    def parse_unary(self) -> Any:
        if self.peek().type == TokenType.MINUS:
            op = self.advance()
            operand = self.parse_unary()
            return UnaryOp(op='-', operand=operand, line=op.line, col=op.col)
        return self.parse_postfix()

    def parse_postfix(self) -> Any:
        expr = self.parse_primary()

        while True:
            if self.peek().type == TokenType.DOT:
                self.advance()
                member_tok = self.peek()
                ident_or_keyword = (
                    TokenType.IDENT, TokenType.WHERE, TokenType.ORDER, TokenType.BY, TokenType.LIMIT,
                    TokenType.EXISTS, TokenType.HAS, TokenType.LIST, TokenType.MAP,
                    TokenType.REPEAT,  # allow as method name (e.g. str.repeat)
                )
                if member_tok.type in ident_or_keyword:
                    member = self.advance().value
                else:
                    member = self.expect(TokenType.IDENT).value
                # Method call
                if self.peek().type == TokenType.LPAREN:
                    self.advance()
                    args, named = self.parse_arg_list()
                    self.expect(TokenType.RPAREN)
                    expr = FunctionCall(
                        name=MemberAccess(object=expr, member=member),
                        args=args, named_args=named
                    )
                else:
                    expr = MemberAccess(object=expr, member=member)
            elif self.peek().type == TokenType.QMARK_DOT:
                self.advance()
                member = self.expect(TokenType.IDENT).value
                expr = OptionalChain(object=expr, member=member)
            elif self.peek().type == TokenType.LPAREN:
                self.advance()
                args, named = self.parse_arg_list()
                self.expect(TokenType.RPAREN)
                expr = FunctionCall(name=expr, args=args, named_args=named)
            elif self.peek().type == TokenType.LBRACKET:
                self.advance()
                index = self.parse_expression()
                self.expect(TokenType.RBRACKET)
                expr = IndexAccess(object=expr, index=index)
            else:
                break
        return expr

    def parse_arg_list(self) -> tuple:
        """Returns (args: list, named_args: dict)."""
        args = []
        named_args = {}
        while self.peek().type != TokenType.RPAREN and self.peek().type != TokenType.EOF:
            if self.peek().type == TokenType.IDENT and self.peek_ahead_type() == TokenType.COLON:
                name_tok = self.advance()
                self.advance()  # consume COLON
                value = self.parse_expression()
                named_args[name_tok.value] = value
            else:
                args.append(self.parse_expression())
            if not self.match(TokenType.COMMA):
                break
        return args, named_args

    def parse_primary(self) -> Any:
        token = self.peek()

        if token.type == TokenType.INT:
            self.advance()
            return IntLiteral(value=int(token.value), line=token.line, col=token.col)

        if token.type == TokenType.FLOAT:
            self.advance()
            return FloatLiteral(value=float(token.value), line=token.line, col=token.col)

        if token.type == TokenType.TEXT:
            self.advance()
            return TextLiteral(value=token.value, line=token.line, col=token.col)

        if token.type == TokenType.BOOL:
            self.advance()
            return BoolLiteral(value=token.value == 'true', line=token.line, col=token.col)

        if token.type == TokenType.NONE:
            # Check if it's a function call: none()
            if self.peek_ahead_type() == TokenType.LPAREN:
                self.advance()
                return Identifier(name='none', line=token.line, col=token.col)
            self.advance()
            return NoneLiteral(line=token.line, col=token.col)

        if token.type == TokenType.IDENT:
            self.advance()
            return Identifier(name=token.value, line=token.line, col=token.col)

        if token.type == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr

        if token.type == TokenType.LBRACKET:
            return self.parse_list_literal()

        if token.type == TokenType.LBRACE:
            return self.parse_map_literal()

        # Keywords that can appear in expressions
        if token.type in (TokenType.SOME, TokenType.MAYBE, TokenType.LIST,
                          TokenType.MAP, TokenType.SET_KW, TokenType.SECRET,
                          TokenType.SENSITIVE, TokenType.NONE, TokenType.TRUE,
                          TokenType.FALSE, TokenType.PORT, TokenType.INPUT,
                          TokenType.LOG):
            self.advance()
            return Identifier(name=token.value, line=token.line, col=token.col)

        raise self.error(f"Неожиданный токен: {token.type.name} ({token.value!r})")

    def parse_list_literal(self) -> ListLiteral:
        token = self.advance()  # consume [
        elements = []
        while self.peek().type != TokenType.RBRACKET and self.peek().type != TokenType.EOF:
            self.skip_newlines()
            elements.append(self.parse_expression())
            self.match(TokenType.COMMA)
            self.skip_newlines()
        self.expect(TokenType.RBRACKET)
        return ListLiteral(elements=elements, line=token.line, col=token.col)

    def parse_map_literal(self) -> MapLiteral:
        token = self.advance()  # consume {
        pairs = []
        while self.peek().type != TokenType.RBRACE and self.peek().type != TokenType.EOF:
            self.skip_newlines()
            key = self.parse_expression()
            self.expect(TokenType.ARROW, "Ожидалось '->' в элементе словаря")
            value = self.parse_expression()
            pairs.append((key, value))
            self.match(TokenType.COMMA)
            self.skip_newlines()
        self.expect(TokenType.RBRACE)
        return MapLiteral(pairs=pairs, line=token.line, col=token.col)


def parse(tokens: List[Token], source: str = "") -> Program:
    """Convenience function to parse tokens into AST."""
    return Parser(tokens, source).parse()
