"""Recursive descent parser for .papa DSL."""

from typing import List, Optional

from .ast_nodes import AgentDef, ConsensusConfig, PipelineDef, Program, SwarmDef
from .lexer import COLON, COMMA, EOF, FRACTION, IDENT, KEYWORD, LBRACE, LBRACKET, NUMBER, RBRACE, RBRACKET, STRING, Token


class ParseError(Exception):
    def __init__(self, message: str, line: int, expected: str = "", got: str = ""):
        msg = f"Parse error at line {line}"
        if expected and got:
            msg += f": expected {expected}, got {got}"
        else:
            msg += f": {message}"
        super().__init__(msg)
        self.line = line


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> Token:
        if self.pos >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        if self.pos < len(self.tokens):
            t = self.tokens[self.pos]
            self.pos += 1
            return t
        return self.tokens[-1]

    def _expect(self, tok_type: str, value: object = None) -> Token:
        t = self._peek()
        if t.type != tok_type:
            raise ParseError("", t.line, tok_type, t.type)
        if value is not None and t.value != value:
            raise ParseError("", t.line, str(value), str(t.value))
        return self._advance()

    def parse(self, source_file: str = "") -> Program:
        program = Program(source_file=source_file)

        while self._peek().type != EOF:
            t = self._peek()
            if t.type == KEYWORD:
                kw = t.value
                if kw == "agent":
                    program.agents.append(self._parse_agent_def())
                elif kw == "swarm":
                    program.swarms.append(self._parse_swarm_def())
                elif kw == "pipeline":
                    program.pipelines.append(self._parse_pipeline_def())
                else:
                    raise ParseError(f"Unexpected keyword {kw}", t.line)
            else:
                raise ParseError(f"Expected agent/swarm/pipeline, got {t.type}", t.line)

        return program

    def _parse_agent_def(self) -> AgentDef:
        self._expect(KEYWORD, "agent")
        name_tok = self._expect(IDENT)
        name = str(name_tok.value)
        line = name_tok.line

        self._expect(LBRACE)

        model = "claude-3-sonnet"
        guard = "standard"
        hrs_threshold = 0.15
        memory = False

        while self._peek().type != RBRACE:
            if self._peek().type != IDENT and self._peek().type != KEYWORD:
                raise ParseError("Expected property name", self._peek().line)
            prop = str(self._advance().value).lower()
            self._expect(COLON)

            if prop == "model":
                t = self._peek()
                if t.type not in (STRING, IDENT):
                    raise ParseError("Expected model name", t.line)
                model = str(self._advance().value)
            elif prop == "guard":
                guard = str(self._expect(IDENT).value).lower()
            elif prop == "hrs_threshold":
                n = self._expect(NUMBER)
                hrs_threshold = float(n.value) if isinstance(n.value, float) else int(n.value)
            elif prop == "memory":
                v = str(self._expect(IDENT).value).lower()
                memory = v == "enabled"
            else:
                self._advance()

        self._expect(RBRACE)
        return AgentDef(
            name=name,
            model=model,
            guard=guard,
            hrs_threshold=hrs_threshold,
            memory=memory,
            line=line,
        )

    def _parse_swarm_def(self) -> SwarmDef:
        self._expect(KEYWORD, "swarm")
        name_tok = self._expect(IDENT)
        name = str(name_tok.value)
        line = name_tok.line

        self._expect(LBRACE)

        agents: List[str] = []
        consensus: Optional[ConsensusConfig] = None
        anchor = "none"
        pii = "none"
        hrs_max = 0.30

        while self._peek().type != RBRACE:
            if self._peek().type not in (IDENT, KEYWORD):
                raise ParseError("Expected property name", self._peek().line)
            prop = str(self._advance().value).lower()
            self._expect(COLON)

            if prop == "agents":
                self._expect(LBRACKET)
                while self._peek().type != RBRACKET:
                    agents.append(str(self._expect(IDENT).value))
                    if self._peek().type == COMMA:
                        self._advance()
                self._expect(RBRACKET)
            elif prop == "consensus":
                f = self._expect(FRACTION)
                req, of_val = f.value
                consensus = ConsensusConfig(required=req, of=of_val)
            elif prop == "anchor":
                anchor = str(self._expect(IDENT).value).lower()
            elif prop == "pii":
                pii = str(self._expect(IDENT).value).lower()
            elif prop == "hrs_max":
                n = self._expect(NUMBER)
                hrs_max = float(n.value) if isinstance(n.value, float) else int(n.value)
            else:
                self._advance()

        self._expect(RBRACE)
        return SwarmDef(
            name=name,
            agents=agents,
            consensus=consensus,
            anchor=anchor,
            pii=pii,
            hrs_max=hrs_max,
            line=line,
        )

    def _parse_pipeline_def(self) -> PipelineDef:
        self._expect(KEYWORD, "pipeline")
        name_tok = self._expect(IDENT)
        name = str(name_tok.value)
        line = name_tok.line

        self._expect(LBRACE)

        route = "orchestrator"
        fallback = "single"
        module = ""

        while self._peek().type != RBRACE:
            if self._peek().type not in (IDENT, KEYWORD):
                raise ParseError("Expected property name", self._peek().line)
            prop = str(self._advance().value).lower()
            self._expect(COLON)

            if prop == "route":
                route = str(self._expect(IDENT).value).lower()
            elif prop == "fallback":
                fallback = str(self._expect(IDENT).value).lower()
            elif prop == "module":
                t = self._peek()
                if t.type == STRING:
                    module = str(self._advance().value)
                else:
                    module = str(self._expect(IDENT).value)
            else:
                self._advance()

        self._expect(RBRACE)
        return PipelineDef(name=name, route=route, fallback=fallback, module=module, line=line)
