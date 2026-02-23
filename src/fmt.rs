//! Code formatter for PAPA Lang.

use crate::lexer::Scanner;
use crate::parser::Parser;
use crate::parser::ast::*;
use std::fmt::Write;

/// Format PL source: parse and pretty-print.
pub fn format_source(source: &str) -> Result<String, String> {
    let mut scanner = Scanner::new(source);
    let tokens = scanner.scan_all();
    let mut parser = Parser::new(tokens);
    let program = parser.parse();
    let mut out = String::new();
    for (i, stmt) in program.statements.iter().enumerate() {
        if i > 0 {
            writeln!(&mut out).map_err(|e| e.to_string())?;
        }
        format_stmt(&mut out, stmt, 0).map_err(|e| e.to_string())?;
    }
    if !program.statements.is_empty() {
        writeln!(&mut out).map_err(|e| e.to_string())?;
    }
    Ok(out)
}

fn indent(f: &mut String, n: usize) -> std::fmt::Result {
    for _ in 0..n {
        write!(f, "  ")?;
    }
    Ok(())
}

fn format_stmt(f: &mut String, stmt: &Stmt, depth: usize) -> Result<(), std::fmt::Error> {
    match stmt {
        Stmt::Let(s) => {
            indent(f, depth)?;
            write!(f, "let {} = ", s.name)?;
            format_expr(f, &s.value)?;
            writeln!(f)?;
        }
        Stmt::Fn(s) => {
            indent(f, depth)?;
            write!(f, "fn {}(", s.name)?;
            for (i, p) in s.params.iter().enumerate() {
                if i > 0 {
                    write!(f, ", ")?;
                }
                write!(f, "{}", p.name)?;
            }
            writeln!(f, ") {{")?;
            for s in &s.body {
                format_stmt(f, s, depth + 1)?;
            }
            indent(f, depth)?;
            writeln!(f, "}}")?;
        }
        Stmt::Type(s) => {
            indent(f, depth)?;
            writeln!(f, "type {} {{", s.name)?;
            for field in &s.fields {
                indent(f, depth + 1)?;
                writeln!(f, "{}: {}", field.name, field.type_ann)?;
            }
            indent(f, depth)?;
            writeln!(f, "}}")?;
        }
        Stmt::Route(r) => {
            indent(f, depth)?;
            writeln!(f, "route {} \"{}\" {{", r.method, r.path)?;
            for s in &r.body {
                format_stmt(f, s, depth + 1)?;
            }
            indent(f, depth)?;
            writeln!(f, "}}")?;
        }
        Stmt::Server(s) => {
            indent(f, depth)?;
            writeln!(f, "server {} {{", s.name)?;
            for item in &s.config {
                indent(f, depth + 1)?;
                write!(f, "{}: ", item.key)?;
                format_expr(f, &item.value)?;
                writeln!(f)?;
            }
            indent(f, depth)?;
            writeln!(f, "}}")?;
        }
        Stmt::Expr(e) => {
            indent(f, depth)?;
            format_expr(f, e)?;
            writeln!(f)?;
        }
    }
    Ok(())
}

fn format_expr(f: &mut String, expr: &Expr) -> Result<(), std::fmt::Error> {
    match expr {
        Expr::Literal(Literal::Int(i)) => write!(f, "{}", i),
        Expr::Literal(Literal::Float(x)) => write!(f, "{}", x),
        Expr::Literal(Literal::Str(s)) => write!(f, "\"{}\"", s.replace('\\', "\\\\").replace('"', "\\\"")),
        Expr::Literal(Literal::Bool(b)) => write!(f, "{}", b),
        Expr::Literal(Literal::None) => write!(f, "none"),
        Expr::Ident(n) => write!(f, "{}", n),
        Expr::Call { callee, args } => {
            format_expr(f, callee)?;
            write!(f, "(")?;
            for (i, a) in args.iter().enumerate() {
                if i > 0 {
                    write!(f, ", ")?;
                }
                format_expr(f, a)?;
            }
            write!(f, ")")
        }
        Expr::Binary { left, op, right } => {
            format_expr(f, left)?;
            write!(f, " {} ", binop_str(op))?;
            format_expr(f, right)
        }
        Expr::Unary { op, expr } => {
            write!(f, "{}", match op {
                UnaryOp::Not => "!",
                UnaryOp::Neg => "-",
            })?;
            format_expr(f, expr)
        }
        Expr::Try(e) => {
            format_expr(f, e)?;
            write!(f, "?")
        }
        Expr::List(items) => {
            write!(f, "[")?;
            for (i, x) in items.iter().enumerate() {
                if i > 0 {
                    write!(f, ", ")?;
                }
                format_expr(f, x)?;
            }
            write!(f, "]")
        }
        Expr::Map(entries) => {
            write!(f, "{{")?;
            for (i, (k, v)) in entries.iter().enumerate() {
                if i > 0 {
                    write!(f, ", ")?;
                }
                write!(f, "{}: ", k)?;
                format_expr(f, v)?;
            }
            write!(f, "}}")
        }
        Expr::Block(stmts) => {
            writeln!(f, "{{")?;
            for s in stmts {
                format_stmt(f, s, 1)?;
            }
            write!(f, "}}")
        }
        Expr::If { cond, then_branch, else_branch } => {
            write!(f, "if ")?;
            format_expr(f, cond)?;
            writeln!(f, " {{")?;
            for s in then_branch {
                format_stmt(f, s, 1)?;
            }
            if let Some(else_stmts) = else_branch {
                writeln!(f, "}} else {{")?;
                for s in else_stmts {
                    format_stmt(f, s, 1)?;
                }
            }
            write!(f, "}}")
        }
        Expr::Match { expr, arms } => {
            write!(f, "match ")?;
            format_expr(f, expr)?;
            writeln!(f, " {{")?;
            for arm in arms {
                write!(f, "  ")?;
                format_pattern(f, &arm.pattern)?;
                if let Some(ref g) = arm.guard {
                    write!(f, " if ")?;
                    format_expr(f, g)?;
                }
                writeln!(f, " => {{")?;
                for s in &arm.body {
                    format_stmt(f, s, 2)?;
                }
                writeln!(f, "  }}")?;
            }
            write!(f, "}}")
        }
        Expr::Pipeline { init, steps } => {
            format_expr(f, init)?;
            for step in steps {
                write!(f, " |> ")?;
                format_expr(f, &step.expr)?;
            }
            Ok(())
        }
        Expr::ListComp { item, var, iter, filter } => {
            write!(f, "[")?;
            format_expr(f, item)?;
            write!(f, " for {} in ", var)?;
            format_expr(f, iter)?;
            if let Some(ref cond) = filter {
                write!(f, " if ")?;
                format_expr(f, cond)?;
            }
            write!(f, "]")
        }
        Expr::StructLiteral { type_name, fields } => {
            write!(f, "{} {{ ", type_name)?;
            for (i, (k, v)) in fields.iter().enumerate() {
                if i > 0 {
                    write!(f, ", ")?;
                }
                write!(f, "{}: ", k)?;
                format_expr(f, v)?;
            }
            write!(f, " }}")
        }
    }
}

fn binop_str(op: &BinOp) -> &'static str {
    use BinOp::*;
    match op {
        Add => "+",
        Sub => "-",
        Mul => "*",
        Div => "/",
        Mod => "%",
        Eq => "==",
        Ne => "!=",
        Lt => "<",
        Gt => ">",
        Le => "<=",
        Ge => ">=",
        And => "&&",
        Or => "||",
        PipeThen | PipeOk | PipeErr => "|>",
    }
}

fn format_pattern(f: &mut String, p: &Pattern) -> Result<(), std::fmt::Error> {
    use crate::parser::ast::Literal;
    use Pattern::*;
    match p {
        Ident(s) => write!(f, "{}", s),
        Literal(lit) => match lit {
            Literal::Int(i) => write!(f, "{}", i),
            Literal::Str(s) => write!(f, "\"{}\"", s),
            Literal::Bool(b) => write!(f, "{}", b),
            Literal::None => write!(f, "none"),
            Literal::Float(x) => write!(f, "{}", x),
        },
        Variant(n, None) => write!(f, "{}", n),
        Variant(n, Some(inner)) => {
            write!(f, "{}( ", n)?;
            format_pattern(f, inner)?;
            write!(f, " )")
        }
        Range(a, b) => {
            format_expr(f, a)?;
            write!(f, "..")?;
            format_expr(f, b)
        }
        Guard(pat, cond) => {
            format_pattern(f, pat)?;
            write!(f, " if ")?;
            format_expr(f, cond)
        }
        MapDestructure(fields) => {
            write!(f, "{{ ")?;
            for (i, (k, sub)) in fields.iter().enumerate() {
                if i > 0 {
                    write!(f, ", ")?;
                }
                if let Some(ref p) = sub {
                    write!(f, "{}: ", k)?;
                    format_pattern(f, p)?;
                } else {
                    write!(f, "{}", k)?;
                }
            }
            write!(f, " }}")
        }
    }
}
