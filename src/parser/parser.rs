//! Recursive descent parser for PAPA Lang.

use crate::lexer::token::{Token, TokenKind};
use crate::parser::ast::*;
use std::iter::Peekable;
use std::vec::IntoIter;

pub struct Parser {
    tokens: Peekable<IntoIter<Token>>,
    current: Option<Token>,
}

impl Parser {
    pub fn new(tokens: Vec<Token>) -> Self {
        let mut tokens = tokens.into_iter().peekable();
        let current = tokens.next();
        Self { tokens, current }
    }

    pub fn parse(&mut self) -> Program {
        let mut statements = Vec::new();
        while !self.is_at_end() {
            if let Some(stmt) = self.parse_stmt() {
                statements.push(stmt);
            }
            self.advance_until_stmt_start();
        }
        Program::new(statements)
    }

    fn advance_until_stmt_start(&mut self) {
        while matches!(
            self.current.as_ref().map(|t| &t.kind),
            Some(TokenKind::Newline) | Some(TokenKind::Semicolon)
        ) {
            self.advance();
        }
    }

    fn parse_stmt(&mut self) -> Option<Stmt> {
        let token = self.current.clone()?;
        match &token.kind {
            TokenKind::Let => self.parse_let(),
            TokenKind::Fn => self.parse_fn(),
            TokenKind::Type => self.parse_type(),
            TokenKind::Route => self.parse_route(),
            TokenKind::Server => self.parse_server(),
            TokenKind::If => self.parse_if(),
            TokenKind::Match => self.parse_match_expr().map(Stmt::Expr),
            _ => self.parse_expr_stmt(),
        }
    }

    fn parse_let(&mut self) -> Option<Stmt> {
        self.advance(); // consume let
        let name = self.expect_ident()?;
        let type_ann = if self.check(TokenKind::Colon) {
            self.advance();
            self.parse_type_ann()
        } else {
            None
        };
        self.expect(TokenKind::Eq)?;
        let value = self.parse_expr()?;
        Some(Stmt::Let(LetStmt {
            name,
            type_ann,
            value,
        }))
    }

    fn parse_fn(&mut self) -> Option<Stmt> {
        self.advance(); // consume fn
        let is_async = false; // TODO: check for async
        let name = self.expect_ident()?;
        self.expect(TokenKind::LParen)?;
        let params = self.parse_params()?;
        self.expect(TokenKind::RParen)?;
        let return_type = if self.check(TokenKind::ReturnType) {
            self.advance();
            self.parse_type_ann()
        } else {
            None
        };
        self.expect(TokenKind::LBrace)?;
        let body = self.parse_block()?;
        self.expect(TokenKind::RBrace)?;
        Some(Stmt::Fn(FnStmt {
            name,
            params,
            return_type,
            body,
            is_async,
        }))
    }

    fn parse_params(&mut self) -> Option<Vec<Param>> {
        let mut params = Vec::new();
        while !self.check(TokenKind::RParen) && !self.is_at_end() {
            let name = self.expect_ident()?;
            let type_ann = if self.check(TokenKind::Colon) {
                self.advance();
                self.parse_type_ann()
            } else {
                None
            };
            params.push(Param { name, type_ann });
            if !self.check(TokenKind::RParen) {
                self.expect(TokenKind::Comma)?;
            }
        }
        Some(params)
    }

    fn parse_block(&mut self) -> Option<Vec<Stmt>> {
        let mut stmts = Vec::new();
        while !self.check(TokenKind::RBrace) && !self.is_at_end() {
            if let Some(s) = self.parse_stmt() {
                stmts.push(s);
            }
            self.advance_until_stmt_start();
        }
        Some(stmts)
    }

    fn parse_type(&mut self) -> Option<Stmt> {
        self.advance(); // consume type
        let name = self.expect_ident()?;
        self.expect(TokenKind::LBrace)?;
        let mut fields = Vec::new();
        while !self.check(TokenKind::RBrace) && !self.is_at_end() {
            let field_name = self.expect_ident()?;
            self.expect(TokenKind::Colon)?;
            let type_ann = self.parse_type_ann().unwrap_or(Type::Ident("any".into()));
            let default = if self.check(TokenKind::Eq) {
                self.advance();
                self.parse_expr()
            } else {
                None
            };
            fields.push(TypeField {
                name: field_name,
                type_ann,
                default,
            });
            if !self.check(TokenKind::RBrace) {
                self.expect(TokenKind::Comma)?;
            }
        }
        self.expect(TokenKind::RBrace)?;
        Some(Stmt::Type(TypeStmt { name, fields }))
    }

    fn parse_route(&mut self) -> Option<Stmt> {
        self.advance();
        let method = self.expect_ident()?;
        let path = if self.check(TokenKind::Str) {
            let s = self.current.as_ref()?.literal.clone();
            self.advance();
            s.trim_matches('"').to_string()
        } else {
            return None;
        };
        let mut attrs = Vec::new();
        while self.check(TokenKind::At) {
            self.advance();
            attrs.push(self.expect_ident()?);
        }
        self.expect(TokenKind::LBrace)?;
        let body = self.parse_block()?;
        self.expect(TokenKind::RBrace)?;
        Some(Stmt::Route(RouteStmt {
            method,
            path,
            attrs,
            body,
        }))
    }

    fn parse_server(&mut self) -> Option<Stmt> {
        self.advance();
        let name = self.expect_ident()?;
        self.expect(TokenKind::LBrace)?;
        let config = self.parse_config_block()?;
        self.expect(TokenKind::RBrace)?;
        Some(Stmt::Server(ServerStmt { name, config }))
    }

    fn parse_config_block(&mut self) -> Option<Vec<ConfigItem>> {
        let mut config = Vec::new();
        while !self.check(TokenKind::RBrace) && !self.is_at_end() {
            let key = self.expect_ident()?;
            self.expect(TokenKind::Colon)?;
            let value = self.parse_expr()?;
            config.push(ConfigItem { key, value });
            if !self.check(TokenKind::RBrace) {
                self.expect(TokenKind::Comma)?;
            }
        }
        Some(config)
    }

    fn parse_if(&mut self) -> Option<Stmt> {
        self.advance();
        let cond = self.parse_expr()?;
        self.expect(TokenKind::LBrace)?;
        let then_branch = self.parse_block()?;
        self.expect(TokenKind::RBrace)?;
        let else_branch = if self.check(TokenKind::Else) {
            self.advance();
            self.expect(TokenKind::LBrace)?;
            let block = self.parse_block()?;
            self.expect(TokenKind::RBrace)?;
            Some(block)
        } else {
            None
        };
        Some(Stmt::Expr(Expr::If {
            cond: Box::new(cond),
            then_branch,
            else_branch,
        }))
    }

    fn parse_expr_stmt(&mut self) -> Option<Stmt> {
        self.parse_expr().map(Stmt::Expr)
    }

    fn parse_expr(&mut self) -> Option<Expr> {
        self.parse_pipeline()
    }

    fn parse_pipeline(&mut self) -> Option<Expr> {
        let init = self.parse_or()?;
        let mut steps = Vec::new();
        while let Some(op) = self.current.as_ref().and_then(|t| match &t.kind {
            TokenKind::PipeThen => Some(PipelineOp::Then),
            TokenKind::PipeOk => Some(PipelineOp::Ok),
            TokenKind::PipeErr => Some(PipelineOp::Err),
            _ => None,
        }) {
            self.advance();
            let rhs = self.parse_or()?;
            steps.push(PipelineStep { op, expr: rhs });
        }
        if steps.is_empty() {
            Some(init)
        } else {
            Some(Expr::Pipeline {
                init: Box::new(init),
                steps,
            })
        }
    }

    fn parse_or(&mut self) -> Option<Expr> {
        let mut left = self.parse_and()?;
        while self.check(TokenKind::OrOr) {
            self.advance();
            let right = self.parse_and()?;
            left = Expr::Binary {
                left: Box::new(left),
                op: BinOp::Or,
                right: Box::new(right),
            };
        }
        Some(left)
    }

    fn parse_and(&mut self) -> Option<Expr> {
        let mut left = self.parse_equality()?;
        while self.check(TokenKind::AndAnd) {
            self.advance();
            let right = self.parse_equality()?;
            left = Expr::Binary {
                left: Box::new(left),
                op: BinOp::And,
                right: Box::new(right),
            };
        }
        Some(left)
    }

    fn parse_equality(&mut self) -> Option<Expr> {
        let mut left = self.parse_comparison()?;
        while let Some(op) = self.current.as_ref().and_then(|t| match &t.kind {
            TokenKind::EqEq => Some(BinOp::Eq),
            TokenKind::NotEq => Some(BinOp::Ne),
            _ => None,
        }) {
            self.advance();
            let right = self.parse_comparison()?;
            left = Expr::Binary {
                left: Box::new(left),
                op,
                right: Box::new(right),
            };
        }
        Some(left)
    }

    fn parse_comparison(&mut self) -> Option<Expr> {
        let mut left = self.parse_term()?;
        while let Some(op) = self.current.as_ref().and_then(|t| match &t.kind {
            TokenKind::Lt => Some(BinOp::Lt),
            TokenKind::Gt => Some(BinOp::Gt),
            TokenKind::LtEq => Some(BinOp::Le),
            TokenKind::GtEq => Some(BinOp::Ge),
            _ => None,
        }) {
            self.advance();
            let right = self.parse_term()?;
            left = Expr::Binary {
                left: Box::new(left),
                op,
                right: Box::new(right),
            };
        }
        Some(left)
    }

    fn parse_term(&mut self) -> Option<Expr> {
        let mut left = self.parse_factor()?;
        while let Some(op) = self.current.as_ref().and_then(|t| match &t.kind {
            TokenKind::Plus => Some(BinOp::Add),
            TokenKind::Minus => Some(BinOp::Sub),
            _ => None,
        }) {
            self.advance();
            let right = self.parse_factor()?;
            left = Expr::Binary {
                left: Box::new(left),
                op,
                right: Box::new(right),
            };
        }
        Some(left)
    }

    fn parse_factor(&mut self) -> Option<Expr> {
        let mut left = self.parse_unary()?;
        while let Some(op) = self.current.as_ref().and_then(|t| match &t.kind {
            TokenKind::Star => Some(BinOp::Mul),
            TokenKind::Slash => Some(BinOp::Div),
            TokenKind::Percent => Some(BinOp::Mod),
            _ => None,
        }) {
            self.advance();
            let right = self.parse_unary()?;
            left = Expr::Binary {
                left: Box::new(left),
                op,
                right: Box::new(right),
            };
        }
        Some(left)
    }

    fn parse_unary(&mut self) -> Option<Expr> {
        if let Some(op) = self.current.as_ref().and_then(|t| match &t.kind {
            TokenKind::Not => Some(UnaryOp::Not),
            TokenKind::Minus => Some(UnaryOp::Neg),
            _ => None,
        }) {
            self.advance();
            let expr = self.parse_unary()?;
            return Some(Expr::Unary {
                op,
                expr: Box::new(expr),
            });
        }
        self.parse_postfix()
    }

    fn parse_postfix(&mut self) -> Option<Expr> {
        let mut expr = self.parse_primary()?;
        while self.check(TokenKind::Question) {
            self.advance();
            expr = Expr::Try(Box::new(expr));
        }
        Some(expr)
    }

    fn parse_primary(&mut self) -> Option<Expr> {
        let token = self.current.clone()?;
        match &token.kind {
            TokenKind::Int => {
                self.advance();
                let i: i64 = token.literal.parse().unwrap_or(0);
                Some(Expr::Literal(Literal::Int(i)))
            }
            TokenKind::Float => {
                self.advance();
                let f: f64 = token.literal.parse().unwrap_or(0.0);
                Some(Expr::Literal(Literal::Float(f)))
            }
            TokenKind::Str => {
                self.advance();
                let s = token.literal.trim_matches(|c| {
                    c == '"' || c == '\'' || c == '\u{201c}' || c == '\u{201d}' || c == '\u{2018}' || c == '\u{2019}'
                }).to_string();
                Some(Expr::Literal(Literal::Str(s)))
            }
            TokenKind::True | TokenKind::False => {
                self.advance();
                Some(Expr::Literal(Literal::Bool(token.kind == TokenKind::True)))
            }
            TokenKind::None_ => {
                self.advance();
                Some(Expr::Literal(Literal::None))
            }
            TokenKind::Ident => {
                let name = token.literal.clone();
                self.advance();
                if self.check(TokenKind::LParen) {
                    self.advance();
                    let mut args = Vec::new();
                    while !self.check(TokenKind::RParen) && !self.is_at_end() {
                        args.push(self.parse_expr()?);
                        if !self.check(TokenKind::RParen) {
                            self.expect(TokenKind::Comma)?;
                        }
                    }
                    self.expect(TokenKind::RParen)?;
                    Some(Expr::Call {
                        callee: Box::new(Expr::Ident(name)),
                        args,
                    })
                } else if self.check(TokenKind::LBrace) {
                    self.advance();
                    let mut fields = Vec::new();
                    while !self.check(TokenKind::RBrace) && !self.is_at_end() {
                        let key = self.expect_ident()?;
                        self.expect(TokenKind::Colon)?;
                        let value = self.parse_expr()?;
                        fields.push((key, value));
                        if !self.check(TokenKind::RBrace) {
                            self.expect(TokenKind::Comma)?;
                        }
                    }
                    self.expect(TokenKind::RBrace)?;
                    Some(Expr::StructLiteral {
                        type_name: name,
                        fields,
                    })
                } else {
                    Some(Expr::Ident(name))
                }
            }
            TokenKind::LParen => {
                self.advance();
                let expr = self.parse_expr()?;
                self.expect(TokenKind::RParen)?;
                Some(expr)
            }
            TokenKind::LBrace => {
                self.advance();
                let mut entries = Vec::new();
                while !self.check(TokenKind::RBrace) && !self.is_at_end() {
                    let key = self.expect_ident()?;
                    self.expect(TokenKind::Colon)?;
                    let value = self.parse_expr()?;
                    entries.push((key, value));
                    if !self.check(TokenKind::RBrace) {
                        self.expect(TokenKind::Comma)?;
                    }
                }
                self.expect(TokenKind::RBrace)?;
                Some(Expr::Map(entries))
            }
            TokenKind::LBracket => self.parse_list_or_comp(),
            TokenKind::Match => self.parse_match_expr(),
            _ => None,
        }
    }

    fn parse_list_or_comp(&mut self) -> Option<Expr> {
        self.advance(); // consume [
        let first = self.parse_expr()?;
        if self.check(TokenKind::For) {
            self.advance(); // consume for
            let var = self.expect_ident()?;
            self.expect(TokenKind::In)?;
            let iter = self.parse_expr()?;
            let filter = if self.check(TokenKind::If) {
                self.advance();
                Some(Box::new(self.parse_expr()?))
            } else {
                None
            };
            self.expect(TokenKind::RBracket)?;
            Some(Expr::ListComp {
                item: Box::new(first),
                var,
                iter: Box::new(iter),
                filter,
            })
        } else {
            let mut items = vec![first];
            while !self.check(TokenKind::RBracket) && !self.is_at_end() {
                self.expect(TokenKind::Comma)?;
                items.push(self.parse_expr()?);
            }
            self.expect(TokenKind::RBracket)?;
            Some(Expr::List(items))
        }
    }

    fn parse_match_expr(&mut self) -> Option<Expr> {
        self.advance(); // consume match
        let expr = self.parse_expr()?;
        self.expect(TokenKind::LBrace)?;
        let mut arms = Vec::new();
        while !self.check(TokenKind::RBrace) && !self.is_at_end() {
            self.advance_until_stmt_start();
            if self.check(TokenKind::RBrace) {
                break;
            }
            let pattern = self.parse_pattern()?;
            let guard = if self.check(TokenKind::If) {
                self.advance(); // consume if
                Some(self.parse_expr()?)
            } else {
                None
            };
            self.expect(TokenKind::Arrow)?;
            let body = self.parse_block()?;
            arms.push(MatchArm {
                pattern,
                guard,
                body,
            });
        }
        self.expect(TokenKind::RBrace)?;
        Some(Expr::Match {
            expr: Box::new(expr),
            arms,
        })
    }

    fn parse_pattern(&mut self) -> Option<Pattern> {
        let pat = self.parse_pattern_base()?;
        if self.check(TokenKind::If) {
            self.advance();
            let cond = self.parse_expr()?;
            Some(Pattern::Guard(Box::new(pat), Box::new(cond)))
        } else {
            Some(pat)
        }
    }

    fn parse_pattern_base(&mut self) -> Option<Pattern> {
        let token = self.current.clone()?;
        match &token.kind {
            TokenKind::Ident => {
                let name = token.literal.clone();
                self.advance();
                // Variant with payload: Ok(x), Err(e)
                if (name == "Ok" || name == "Err") && self.check(TokenKind::LParen) {
                    self.advance();
                    let inner = if self.check(TokenKind::RParen) {
                        None
                    } else {
                        let p = self.parse_pattern_base()?;
                        self.expect(TokenKind::RParen)?;
                        Some(Box::new(p))
                    };
                    Some(Pattern::Variant(name, inner))
                } else {
                    Some(Pattern::Ident(name))
                }
            }
            TokenKind::Int | TokenKind::Float
                if self.tokens.peek().map_or(false, |t| t.kind == TokenKind::DotDot) =>
            {
                let start = self.parse_expr()?;
                self.expect(TokenKind::DotDot)?;
                let end = self.parse_expr()?;
                Some(Pattern::Range(Box::new(start), Box::new(end)))
            }
            TokenKind::Int => {
                self.advance();
                let i: i64 = token.literal.parse().unwrap_or(0);
                Some(Pattern::Literal(Literal::Int(i)))
            }
            TokenKind::Float => {
                self.advance();
                let f: f64 = token.literal.parse().unwrap_or(0.0);
                Some(Pattern::Literal(Literal::Float(f)))
            }
            TokenKind::Str => {
                self.advance();
                let s = token.literal.trim_matches('"').to_string();
                Some(Pattern::Literal(Literal::Str(s)))
            }
            TokenKind::True | TokenKind::False => {
                self.advance();
                Some(Pattern::Literal(Literal::Bool(token.kind == TokenKind::True)))
            }
            TokenKind::None_ => {
                self.advance();
                Some(Pattern::Literal(Literal::None))
            }
            TokenKind::LBrace => {
                self.advance();
                let mut fields = Vec::new();
                while !self.check(TokenKind::RBrace) && !self.is_at_end() {
                    let key = self.expect_ident()?;
                    let inner = if self.check(TokenKind::Colon) {
                        self.advance();
                        Some(self.parse_pattern()?)
                    } else {
                        None
                    };
                    fields.push((key, inner));
                    if !self.check(TokenKind::RBrace) {
                        self.expect(TokenKind::Comma)?;
                    }
                }
                self.expect(TokenKind::RBrace)?;
                Some(Pattern::MapDestructure(fields))
            }
            _ => None,
        }
    }

    fn parse_type_ann(&mut self) -> Option<Type> {
        let token = self.current.clone()?;
        match &token.kind {
            TokenKind::Ident => {
                let name = token.literal.clone();
                self.advance();
                if self.check(TokenKind::Question) {
                    self.advance();
                    Some(Type::Optional(Box::new(Type::Ident(name))))
                } else {
                    Some(Type::Ident(name))
                }
            }
            TokenKind::LBracket => {
                self.advance();
                let inner = self.parse_type_ann()?;
                self.expect(TokenKind::RBracket)?;
                Some(Type::Array(Box::new(inner)))
            }
            _ => None,
        }
    }

    fn advance(&mut self) {
        self.current = self.tokens.next();
    }

    fn check(&self, kind: TokenKind) -> bool {
        self.current.as_ref().map_or(false, |t| t.kind == kind)
    }

    fn is_at_end(&self) -> bool {
        self.current
            .as_ref()
            .map_or(true, |t| matches!(t.kind, TokenKind::Eof))
    }

    fn expect(&mut self, kind: TokenKind) -> Option<()> {
        if self.check(kind) {
            self.advance();
            Some(())
        } else {
            None
        }
    }

    fn expect_ident(&mut self) -> Option<String> {
        if let Some(TokenKind::Ident) = self.current.as_ref().map(|t| &t.kind) {
            let name = self.current.as_ref().unwrap().literal.clone();
            self.advance();
            Some(name)
        } else {
            None
        }
    }
}
