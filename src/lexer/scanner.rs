//! Lexer / tokenizer for PAPA Lang.

use crate::lexer::token::{Token, TokenKind};

/// Scans PL source into tokens.
pub struct Scanner {
    source: Vec<char>,
    line: usize,
    column: usize,
    start: usize,
    current: usize,
}

impl Scanner {
    pub fn new(source: &str) -> Self {
        Self {
            source: source.chars().collect(),
            line: 1,
            column: 1,
            start: 0,
            current: 0,
        }
    }

    pub fn scan_all(&mut self) -> Vec<Token> {
        let mut tokens = Vec::new();
        loop {
            let token = self.scan_token();
            let is_eof = matches!(token.kind, TokenKind::Eof);
            tokens.push(token);
            if is_eof {
                break;
            }
        }
        tokens
    }

    fn scan_token(&mut self) -> Token {
        self.skip_whitespace_and_comments();
        self.start = self.current;

        if self.is_at_end() {
            return self.make_token(TokenKind::Eof);
        }

        let c = self.advance();

        // Single/double char operators
        match c {
            '\n' => {
                self.line += 1;
                self.column = 1;
                return self.make_token(TokenKind::Newline);
            }
            '(' => return self.make_token(TokenKind::LParen),
            ')' => return self.make_token(TokenKind::RParen),
            '{' => return self.make_token(TokenKind::LBrace),
            '}' => return self.make_token(TokenKind::RBrace),
            '[' => return self.make_token(TokenKind::LBracket),
            ']' => return self.make_token(TokenKind::RBracket),
            ',' => return self.make_token(TokenKind::Comma),
            ':' => {
                if self.match_char(':') {
                    return self.make_token(TokenKind::ColonColon);
                }
                return self.make_token(TokenKind::Colon);
            }
            ';' => return self.make_token(TokenKind::Semicolon),
            '+' => {
                if self.match_char('=') {
                    return self.make_token(TokenKind::PlusEq);
                }
                return self.make_token(TokenKind::Plus);
            }
            '-' => {
                if self.match_char('>') {
                    return self.make_token(TokenKind::ReturnType);
                }
                if self.match_char('=') {
                    return self.make_token(TokenKind::MinusEq);
                }
                return self.make_token(TokenKind::Minus);
            }
            '*' => return self.make_token(TokenKind::Star),
            '/' => return self.make_token(TokenKind::Slash),
            '%' => return self.make_token(TokenKind::Percent),
            '!' => {
                if self.match_char('=') {
                    return self.make_token(TokenKind::NotEq);
                }
                return self.make_token(TokenKind::Not);
            }
            '=' => {
                if self.match_char('=') {
                    return self.make_token(TokenKind::EqEq);
                }
                if self.match_char('>') {
                    return self.make_token(TokenKind::Arrow);
                }
                return self.make_token(TokenKind::Eq);
            }
            '<' => {
                if self.match_char('=') {
                    return self.make_token(TokenKind::LtEq);
                }
                return self.make_token(TokenKind::Lt);
            }
            '>' => {
                if self.match_char('=') {
                    return self.make_token(TokenKind::GtEq);
                }
                // Check for |>
                return self.make_token(TokenKind::Gt);
            }
            '&' => {
                if self.match_char('&') {
                    return self.make_token(TokenKind::AndAnd);
                }
                // Invalid, treat as ident start
            }
            '|' => {
                if self.match_char('>') {
                    return self.make_token(TokenKind::PipeThen);
                }
                if self.match_char('?') && self.match_char('>') {
                    return self.make_token(TokenKind::PipeOk);
                }
                if self.match_char('!') && self.match_char('>') {
                    return self.make_token(TokenKind::PipeErr);
                }
            }
            '?' => return self.make_token(TokenKind::Question),
            '.' => {
                if self.match_char('.') {
                    return self.make_token(TokenKind::DotDot);
                }
                return self.make_token(TokenKind::Dot);
            }
            '@' => return self.make_token(TokenKind::At),
            '"' => return self.string('"'),
            '\'' => return self.string('\''),
            'b' if self.peek() == Some('"') || self.peek() == Some('\'') => {
                let quote = self.peek().unwrap();
                self.advance(); // consume opening quote
                return self.bytes_literal(quote);
            }
            '0'..='9' => return self.number(),
            _ if c.is_alphabetic() || c == '_' => return self.identifier(),
            _ => {}
        }

        self.make_token(TokenKind::Ident) // fallback for unknown
    }

    fn skip_whitespace_and_comments(&mut self) {
        loop {
            match self.peek() {
                Some(' ') | Some('\t') | Some('\r') => {
                    self.advance();
                    self.column += 1;
                }
                Some('/') if self.peek_next() == Some('/') => {
                    while self.peek() != Some('\n') && !self.is_at_end() {
                        self.advance();
                    }
                }
                _ => break,
            }
        }
    }

    fn string(&mut self, quote: char) -> Token {
        while self.peek() != Some(quote) && !self.is_at_end() {
            if self.peek() == Some('\n') {
                self.line += 1;
                self.column = 1;
            }
            if self.peek() == Some('\\') {
                self.advance();
            }
            self.advance();
        }
        if self.is_at_end() {
            return self.make_token(TokenKind::Str); // Unterminated
        }
        self.advance(); // closing quote
        self.make_token(TokenKind::Str)
    }

    fn bytes_literal(&mut self, quote: char) -> Token {
        while self.peek() != Some(quote) && !self.is_at_end() {
            if self.peek() == Some('\\') {
                self.advance();
            }
            self.advance();
        }
        if !self.is_at_end() {
            self.advance();
        }
        self.make_token(TokenKind::Bytes)
    }

    fn number(&mut self) -> Token {
        while self.peek().map_or(false, |c| c.is_ascii_digit()) {
            self.advance();
        }
        if self.peek() == Some('.') && self.peek_next().map_or(false, |c| c.is_ascii_digit()) {
            self.advance();
            while self.peek().map_or(false, |c| c.is_ascii_digit()) {
                self.advance();
            }
            return self.make_token(TokenKind::Float);
        }
        self.make_token(TokenKind::Int)
    }

    fn identifier(&mut self) -> Token {
        while self
            .peek()
            .map_or(false, |c| c.is_alphanumeric() || c == '_')
        {
            self.advance();
        }
        // Support dotted identifiers: db.sql, cache.set
        while self.peek() == Some('.')
            && self.peek_next().map_or(false, |c| c.is_alphabetic() || c == '_')
        {
            self.advance(); // consume '.'
            while self
                .peek()
                .map_or(false, |c| c.is_alphanumeric() || c == '_')
            {
                self.advance();
            }
        }
        let literal: String = self.source[self.start..self.current].iter().collect();
        let kind = TokenKind::from_keyword(&literal).unwrap_or(TokenKind::Ident);
        self.make_token_with_literal(kind, literal)
    }

    fn advance(&mut self) -> char {
        if self.is_at_end() {
            return '\0';
        }
        let c = self.source[self.current];
        self.current += 1;
        self.column += 1;
        c
    }

    fn peek(&self) -> Option<char> {
        if self.current >= self.source.len() {
            None
        } else {
            Some(self.source[self.current])
        }
    }

    fn peek_next(&self) -> Option<char> {
        if self.current + 1 >= self.source.len() {
            None
        } else {
            Some(self.source[self.current + 1])
        }
    }

    fn match_char(&mut self, expected: char) -> bool {
        if self.peek() == Some(expected) {
            self.advance();
            true
        } else {
            false
        }
    }

    fn is_at_end(&self) -> bool {
        self.current >= self.source.len()
    }

    fn make_token(&self, kind: TokenKind) -> Token {
        let literal: String = self.source[self.start..self.current].iter().collect();
        let len = literal.len();
        Token::new(kind, literal, self.line, self.column.saturating_sub(len))
    }

    fn make_token_with_literal(&self, kind: TokenKind, literal: String) -> Token {
        let len = literal.len();
        Token::new(kind, literal, self.line, self.column.saturating_sub(len))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn scan_keywords() {
        let mut s = Scanner::new("let fn if else true false");
        let tokens = s.scan_all();
        assert_eq!(tokens[0].kind, TokenKind::Let);
        assert_eq!(tokens[1].kind, TokenKind::Fn);
        assert_eq!(tokens[2].kind, TokenKind::If);
        assert_eq!(tokens[3].kind, TokenKind::Else);
        assert_eq!(tokens[4].kind, TokenKind::True);
        assert_eq!(tokens[5].kind, TokenKind::False);
    }

    #[test]
    fn scan_operators() {
        let mut s = Scanner::new("|> => -> == != + - * /");
        let tokens = s.scan_all();
        assert_eq!(tokens[0].kind, TokenKind::PipeThen);
        assert_eq!(tokens[1].kind, TokenKind::Arrow);
        assert_eq!(tokens[2].kind, TokenKind::ReturnType);
    }

    #[test]
    fn scan_string() {
        let mut s = Scanner::new(r#""hello world""#);
        let tokens = s.scan_all();
        assert_eq!(tokens[0].kind, TokenKind::Str);
    }

    #[test]
    fn scan_number() {
        let mut s = Scanner::new("42 3.14");
        let tokens = s.scan_all();
        assert_eq!(tokens[0].kind, TokenKind::Int);
        assert_eq!(tokens[1].kind, TokenKind::Float);
    }
}
