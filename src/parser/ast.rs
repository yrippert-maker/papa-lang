//! AST (Abstract Syntax Tree) node types for PAPA Lang.

use std::fmt;

/// Root node — collection of statements.
#[derive(Debug, Clone)]
pub struct Program {
    pub statements: Vec<Stmt>,
}

impl Program {
    pub fn new(statements: Vec<Stmt>) -> Self {
        Self { statements }
    }
}

/// Statement types.
#[derive(Debug, Clone)]
pub enum Stmt {
    Let(LetStmt),
    Fn(FnStmt),
    Type(TypeStmt),
    Route(RouteStmt),
    Server(ServerStmt),
    Expr(Expr),
}

/// `let name: Type = value`
#[derive(Debug, Clone)]
pub struct LetStmt {
    pub name: String,
    pub type_ann: Option<Type>,
    pub value: Expr,
}

/// `fn name(params) -> ReturnType { body }`
#[derive(Debug, Clone)]
pub struct FnStmt {
    pub name: String,
    pub params: Vec<Param>,
    pub return_type: Option<Type>,
    pub body: Vec<Stmt>,
    pub is_async: bool,
}

#[derive(Debug, Clone)]
pub struct Param {
    pub name: String,
    pub type_ann: Option<Type>,
}

/// `type Name { ... }`
#[derive(Debug, Clone)]
pub struct TypeStmt {
    pub name: String,
    pub fields: Vec<TypeField>,
}

#[derive(Debug, Clone)]
pub struct TypeField {
    pub name: String,
    pub type_ann: Type,
    pub default: Option<Expr>,
}

/// `route GET "/path" { ... }`
#[derive(Debug, Clone)]
pub struct RouteStmt {
    pub method: String,
    pub path: String,
    pub attrs: Vec<String>,
    pub body: Vec<Stmt>,
}

/// `server name { ... }`
#[derive(Debug, Clone)]
pub struct ServerStmt {
    pub name: String,
    pub config: Vec<ConfigItem>,
}

#[derive(Debug, Clone)]
pub struct ConfigItem {
    pub key: String,
    pub value: Expr,
}

/// Type annotations.
#[derive(Debug, Clone, PartialEq)]
pub enum Type {
    Ident(String),
    Optional(Box<Type>),
    Array(Box<Type>),
    Map(Box<Type>, Box<Type>),
    Result(Box<Type>, Box<Type>),
}

impl fmt::Display for Type {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Type::Ident(s) => write!(f, "{}", s),
            Type::Optional(t) => write!(f, "{}?", t),
            Type::Array(t) => write!(f, "[{}]", t),
            Type::Map(k, v) => write!(f, "{{{}: {}}}", k, v),
            Type::Result(ok, err) => write!(f, "result<{}, {}>", ok, err),
        }
    }
}

/// Expression types.
#[derive(Debug, Clone)]
pub enum Expr {
    Literal(Literal),
    Ident(String),
    Binary {
        left: Box<Expr>,
        op: BinOp,
        right: Box<Expr>,
    },
    Unary {
        op: UnaryOp,
        expr: Box<Expr>,
    },
    Call {
        callee: Box<Expr>,
        args: Vec<Expr>,
    },
    Pipeline {
        init: Box<Expr>,
        steps: Vec<PipelineStep>,
    },
    Block(Vec<Stmt>),
    If {
        cond: Box<Expr>,
        then_branch: Vec<Stmt>,
        else_branch: Option<Vec<Stmt>>,
    },
    Match {
        expr: Box<Expr>,
        arms: Vec<MatchArm>,
    },
    /// Object/map literal { key: value, ... }
    Map(Vec<(String, Expr)>),
    /// Array literal [ a, b, c ]
    List(Vec<Expr>),
}

#[derive(Debug, Clone, PartialEq)]
pub enum BinOp {
    Add,
    Sub,
    Mul,
    Div,
    Mod,
    Eq,
    Ne,
    Lt,
    Gt,
    Le,
    Ge,
    And,
    Or,
    PipeThen,
    PipeOk,
    PipeErr,
}

#[derive(Debug, Clone, PartialEq)]
pub enum UnaryOp {
    Not,
    Neg,
}

#[derive(Debug, Clone)]
pub struct PipelineStep {
    pub op: PipelineOp,
    pub expr: Expr,
}

#[derive(Debug, Clone, PartialEq)]
pub enum PipelineOp {
    Then,  // |>
    Ok,    // |?>
    Err,   // |!>
}

#[derive(Debug, Clone)]
pub struct MatchArm {
    pub pattern: Pattern,
    pub body: Vec<Stmt>,
}

#[derive(Debug, Clone)]
pub enum Pattern {
    Ident(String),
    Literal(Literal),
    Variant(String),
}

#[derive(Debug, Clone, PartialEq)]
pub enum Literal {
    Int(i64),
    Float(f64),
    Str(String),
    Bool(bool),
    None,
}
