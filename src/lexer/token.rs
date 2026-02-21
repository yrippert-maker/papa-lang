//! PL token types for lexer output.

use std::fmt;

/// A single token from the PL source.
#[derive(Debug, Clone, PartialEq)]
pub struct Token {
    pub kind: TokenKind,
    pub literal: String,
    pub line: usize,
    pub column: usize,
}

impl Token {
    pub fn new(kind: TokenKind, literal: impl Into<String>, line: usize, column: usize) -> Self {
        Self {
            kind,
            literal: literal.into(),
            line,
            column,
        }
    }

    pub fn eof(line: usize, column: usize) -> Self {
        Self::new(TokenKind::Eof, "", line, column)
    }
}

impl fmt::Display for Token {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.literal)
    }
}

/// All token kinds for PAPA Lang.
#[derive(Debug, Clone, PartialEq)]
pub enum TokenKind {
    // Literals
    Ident,
    Int,
    Float,
    Str,
    Bytes,
    Bool,
    Uuid,
    Timestamp,

    // Keywords
    Let,
    Fn,
    Async,
    Type,
    Enum,
    Trait,
    Impl,
    Use,
    Module,
    Pub,
    Match,
    If,
    Else,
    For,
    In,
    While,
    Return,
    Route,
    Server,
    Deploy,
    Db,
    Ai,
    Cache,
    Queue,
    Secrets,
    Metrics,
    Log,
    Alert,
    Schedule,
    Firewall,
    Health,
    Storage,
    Middleware,
    Sandbox,
    Env,
    None_,
    Some_,
    Ok_,
    Err_,
    True,
    False,

    // Operators
    PipeThen,   // |>
    PipeOk,     // |?>
    PipeErr,    // |!>
    Arrow,      // =>
    ReturnType, // ->
    At,
    ColonColon,
    Dot,
    DotDot,
    Question,
    Plus,
    Minus,
    Star,
    Slash,
    Percent,
    EqEq,
    NotEq,
    Lt,
    Gt,
    LtEq,
    GtEq,
    AndAnd,
    OrOr,
    Not,
    Eq,
    PlusEq,
    MinusEq,

    // Delimiters
    LParen,
    RParen,
    LBrace,
    RBrace,
    LBracket,
    RBracket,
    Comma,
    Colon,
    Semicolon,
    Newline,

    // Special
    Eof,
}

impl TokenKind {
    /// Check if this token kind is a keyword that could be an identifier.
    pub fn is_keyword(s: &str) -> bool {
        matches!(
            s,
            "let" | "fn" | "async" | "type" | "enum" | "trait" | "impl" | "use" | "module"
                | "pub" | "match" | "if" | "else" | "for" | "in" | "while" | "return"
                | "route" | "server" | "deploy" | "db" | "ai" | "cache" | "queue"
                | "secrets" | "metrics" | "log" | "alert" | "schedule" | "firewall"
                | "health" | "storage" | "middleware" | "sandbox" | "env"
                | "none" | "some" | "ok" | "err" | "true" | "false"
        )
    }

    pub fn from_keyword(s: &str) -> Option<Self> {
        Some(match s {
            "let" => TokenKind::Let,
            "fn" => TokenKind::Fn,
            "async" => TokenKind::Async,
            "type" => TokenKind::Type,
            "enum" => TokenKind::Enum,
            "trait" => TokenKind::Trait,
            "impl" => TokenKind::Impl,
            "use" => TokenKind::Use,
            "module" => TokenKind::Module,
            "pub" => TokenKind::Pub,
            "match" => TokenKind::Match,
            "if" => TokenKind::If,
            "else" => TokenKind::Else,
            "for" => TokenKind::For,
            "in" => TokenKind::In,
            "while" => TokenKind::While,
            "return" => TokenKind::Return,
            "route" => TokenKind::Route,
            "server" => TokenKind::Server,
            "deploy" => TokenKind::Deploy,
            "db" => TokenKind::Db,
            "ai" => TokenKind::Ai,
            "cache" => TokenKind::Cache,
            "queue" => TokenKind::Queue,
            "secrets" => TokenKind::Secrets,
            "metrics" => TokenKind::Metrics,
            "log" => TokenKind::Log,
            "alert" => TokenKind::Alert,
            "schedule" => TokenKind::Schedule,
            "firewall" => TokenKind::Firewall,
            "health" => TokenKind::Health,
            "storage" => TokenKind::Storage,
            "middleware" => TokenKind::Middleware,
            "sandbox" => TokenKind::Sandbox,
            "env" => TokenKind::Env,
            "none" => TokenKind::None_,
            "some" => TokenKind::Some_,
            "ok" => TokenKind::Ok_,
            "err" => TokenKind::Err_,
            "true" => TokenKind::True,
            "false" => TokenKind::False,
            _ => return None,
        })
    }
}
