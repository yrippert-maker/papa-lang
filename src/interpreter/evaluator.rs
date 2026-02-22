//! Tree-walking evaluator for PL AST.

use super::builtins;
use crate::runtime;
use crate::parser::ast::*;
use crate::interpreter::value::Value;
use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;

pub type Env = Rc<RefCell<Environment>>;

#[derive(Debug, Default)]
pub struct Environment {
    values: HashMap<String, Value>,
    parent: Option<Env>,
}

impl Environment {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn with_parent(parent: Env) -> Self {
        Self {
            values: HashMap::new(),
            parent: Some(parent),
        }
    }

    pub fn define(&mut self, name: &str, value: Value) {
        let key = name.trim().to_string();
        self.values.insert(key, value);
    }

    pub fn get(&self, name: &str) -> Option<Value> {
        let key = name.trim();
        if let Some(v) = self.values.get(key) {
            return Some(v.clone());
        }
        if let Some(ref parent) = self.parent {
            return parent.borrow().get(name);
        }
        None
    }

    pub fn set(&mut self, name: &str, value: Value) -> bool {
        let key = name.trim();
        if self.values.contains_key(key) {
            self.values.insert(key.to_string(), value);
            return true;
        }
        if let Some(ref parent) = self.parent {
            return parent.borrow_mut().set(name, value);
        }
        false
    }
}

pub struct Evaluator {
    env: Env,
}

impl Evaluator {
    pub fn new() -> Self {
        let env = Rc::new(RefCell::new(Environment::new()));
        builtins::register_all(&mut env.borrow_mut());
        Self { env }
    }

    pub fn with_env(env: Env) -> Self {
        Self { env }
    }

    pub fn eval_program(&mut self, program: &Program) -> Result<Value, String> {
        let mut last = Value::None;
        for stmt in &program.statements {
            last = self.eval_stmt(stmt)?;
        }
        Ok(last)
    }

    fn eval_stmt(&mut self, stmt: &Stmt) -> Result<Value, String> {
        match stmt {
            Stmt::Let(s) => {
                let value = self.eval_expr(&s.value)?;
                self.env.borrow_mut().define(&s.name, value.clone());
                Ok(value)
            }
            Stmt::Fn(s) => {
                let params: Vec<String> = s.params.iter().map(|p| p.name.trim().to_string()).collect();
                let value = Value::Function {
                    name: s.name.trim().to_string(),
                    params: params.clone(),
                    body: s.body.clone(),
                };
                self.env.borrow_mut().define(&s.name, value);
                Ok(Value::None)
            }
            Stmt::Type(_) => Ok(Value::None),
            Stmt::Server(s) => self.eval_server(s),
            Stmt::Route(r) => self.eval_route(r),
            Stmt::Expr(e) => self.eval_expr(e),
        }
    }

    fn eval_expr(&mut self, expr: &Expr) -> Result<Value, String> {
        match expr {
            Expr::Literal(lit) => Ok(self.literal_to_value(lit)),
            Expr::Ident(name) => self
                .env
                .borrow()
                .get(name)
                .ok_or_else(|| format!("Undefined variable: {}", name)),
            Expr::Binary { left, op, right } => {
                let l = self.eval_expr(left)?;
                let r = self.eval_expr(right)?;
                self.eval_binary(l, op, r)
            }
            Expr::Unary { op, expr } => {
                let v = self.eval_expr(expr)?;
                self.eval_unary(op, v)
            }
            Expr::Call { callee, args } => {
                let f = self.eval_expr(callee)?;
                let arg_values: Vec<Value> = args
                    .iter()
                    .map(|a| self.eval_expr(a))
                    .collect::<Result<Vec<_>, _>>()?;
                self.call(f, &arg_values)
            }
            Expr::If {
                cond,
                then_branch,
                else_branch,
            } => {
                let c = self.eval_expr(cond)?;
                if c.is_truthy() {
                    self.eval_block(then_branch)
                } else if let Some(else_stmts) = else_branch {
                    self.eval_block(else_stmts)
                } else {
                    Ok(Value::None)
                }
            }
            Expr::Block(stmts) => self.eval_block(stmts),
            Expr::Pipeline { init, steps } => {
                let mut val = self.eval_expr(init)?;
                for step in steps {
                    val = self.eval_pipeline_step(val, &step.expr)?;
                }
                Ok(val)
            }
            Expr::Match { .. } => Err("match not implemented yet".into()),
            Expr::Map(entries) => {
                let mut m = HashMap::new();
                for (k, e) in entries {
                    let v = self.eval_expr(e)?;
                    m.insert(k.to_string(), v);
                }
                Ok(Value::Map(m))
            }
            Expr::List(items) => {
                let mut lst = Vec::new();
                for e in items {
                    lst.push(self.eval_expr(e)?);
                }
                Ok(Value::List(lst))
            }
        }
    }

    fn literal_to_value(&self, lit: &Literal) -> Value {
        match lit {
            Literal::Int(i) => Value::Int(*i),
            Literal::Float(f) => Value::Float(*f),
            Literal::Str(s) => Value::Str(interpolate_str(s, &self.env)),
            Literal::Bool(b) => Value::Bool(*b),
            Literal::None => Value::None,
        }
    }

    fn eval_binary(&self, left: Value, op: &BinOp, right: Value) -> Result<Value, String> {
        use BinOp::*;
        match op {
            Add => match (&left, &right) {
                (Value::Int(a), Value::Int(b)) => Ok(Value::Int(a + b)),
                (Value::Float(a), Value::Float(b)) => Ok(Value::Float(a + b)),
                (Value::Str(a), Value::Str(b)) => Ok(Value::Str(format!("{}{}", a, b))),
                (Value::Str(a), b) => Ok(Value::Str(format!("{}{}", a, b))),
                (a, Value::Str(b)) => Ok(Value::Str(format!("{}{}", a, b))),
                _ => Err(format!("Invalid operands for +: {} and {}", left, right)),
            },
            Sub => match (left.as_int(), right.as_int()) {
                (Some(a), Some(b)) => Ok(Value::Int(a - b)),
                _ => Err("Cannot subtract non-integers".into()),
            },
            Mul => match (left.as_int(), right.as_int()) {
                (Some(a), Some(b)) => Ok(Value::Int(a * b)),
                _ => Err("Cannot multiply non-integers".into()),
            },
            Div => match (left.as_int(), right.as_int()) {
                (Some(a), Some(b)) => {
                    if b == 0 {
                        Err("Division by zero".into())
                    } else {
                        Ok(Value::Int(a / b))
                    }
                }
                _ => Err("Cannot divide non-integers".into()),
            },
            Mod => match (left.as_int(), right.as_int()) {
                (Some(a), Some(b)) => Ok(Value::Int(a % b)),
                _ => Err("Cannot mod non-integers".into()),
            },
            Eq => Ok(Value::Bool(value_eq(&left, &right))),
            Ne => Ok(Value::Bool(!value_eq(&left, &right))),
            Lt => match (left.as_int(), right.as_int()) {
                (Some(a), Some(b)) => Ok(Value::Bool(a < b)),
                _ => Err("Cannot compare non-integers with <".into()),
            },
            Gt => match (left.as_int(), right.as_int()) {
                (Some(a), Some(b)) => Ok(Value::Bool(a > b)),
                _ => Err("Cannot compare non-integers with >".into()),
            },
            Le => match (left.as_int(), right.as_int()) {
                (Some(a), Some(b)) => Ok(Value::Bool(a <= b)),
                _ => Err("Cannot compare non-integers with <=".into()),
            },
            Ge => match (left.as_int(), right.as_int()) {
                (Some(a), Some(b)) => Ok(Value::Bool(a >= b)),
                _ => Err("Cannot compare non-integers with >=".into()),
            },
            And => Ok(Value::Bool(left.is_truthy() && right.is_truthy())),
            Or => Ok(Value::Bool(left.is_truthy() || right.is_truthy())),
            PipeThen | PipeOk | PipeErr => Err("Pipeline ops in binary form not implemented".into()),
        }
    }

    fn eval_unary(&self, op: &UnaryOp, v: Value) -> Result<Value, String> {
        match op {
            UnaryOp::Not => Ok(Value::Bool(!v.is_truthy())),
            UnaryOp::Neg => match v {
                Value::Int(i) => Ok(Value::Int(-i)),
                Value::Float(f) => Ok(Value::Float(-f)),
                _ => Err("Cannot negate non-number".into()),
            },
        }
    }

    fn eval_block(&mut self, stmts: &[Stmt]) -> Result<Value, String> {
        let mut last = Value::None;
        for s in stmts {
            last = self.eval_stmt(s)?;
        }
        Ok(last)
    }

    fn eval_server(&mut self, s: &crate::parser::ast::ServerStmt) -> Result<Value, String> {
        let mut port = 8080u16;
        let mut host = "0.0.0.0".to_string();
        for item in &s.config {
            let val = self.eval_expr(&item.value)?;
            match item.key.as_str() {
                "port" => port = val.as_int().unwrap_or(8080) as u16,
                "host" => host = val.to_string(),
                _ => {}
            }
        }
        // Override from env if set (e.g. pl serve file.pl --port 9080)
        if let Ok(p) = std::env::var("PAPA_PORT") {
            if let Ok(n) = p.parse::<u16>() {
                port = n;
            }
        }
        let rt = runtime::RUNTIME.write().map_err(|e| e.to_string())?;
        rt.http.write().map_err(|e| e.to_string())?.set_config(port, &host);
        Ok(Value::None)
    }

    fn eval_route(&mut self, r: &crate::parser::ast::RouteStmt) -> Result<Value, String> {
        let response = self.eval_block(&r.body)?;
        let response_json = response.to_json();
        let rt = runtime::RUNTIME.write().map_err(|e| e.to_string())?;
        rt.http.write().map_err(|e| e.to_string())?.add_route(
            &r.method,
            &r.path,
            response_json,
        );
        Ok(Value::None)
    }

    fn eval_pipeline_step(&mut self, input: Value, expr: &Expr) -> Result<Value, String> {
        match expr {
            Expr::Call { callee, args } => {
                let f = self.eval_expr(callee)?;
                let mut all_args = vec![input];
                all_args.extend(args.iter().map(|a| self.eval_expr(a)).collect::<Result<Vec<_>, _>>()?);
                self.call(f, &all_args)
            }
            _ => Err("Pipeline step must be a call".into()),
        }
    }

    fn call(&mut self, callee: Value, args: &[Value]) -> Result<Value, String> {
        match callee {
            Value::Function {
                params,
                body,
                ..
            } => {
                let child_env = Rc::new(RefCell::new(Environment::with_parent(self.env.clone())));
                for (i, param) in params.iter().enumerate() {
                    let val = args.get(i).cloned().unwrap_or(Value::None);
                    child_env.borrow_mut().define(param, val);
                }
                let mut inner = Evaluator::with_env(child_env);
                let mut last = Value::None;
                for stmt in &body {
                    last = inner.eval_stmt(stmt)?;
                }
                Ok(last)
            }
            Value::Builtin(name) => builtins::call(&name, args),
            _ => Err(format!("Cannot call non-function: {}", callee)),
        }
    }

}

/// Interpolate {var} in string using environment.
fn value_eq(a: &Value, b: &Value) -> bool {
    match (a, b) {
        (Value::Int(x), Value::Int(y)) => x == y,
        (Value::Float(x), Value::Float(y)) => (x - y).abs() < f64::EPSILON,
        (Value::Str(x), Value::Str(y)) => x == y,
        (Value::Bool(x), Value::Bool(y)) => x == y,
        (Value::None, Value::None) => true,
        (Value::List(x), Value::List(y)) => x.len() == y.len() && x.iter().zip(y.iter()).all(|(a, b)| value_eq(a, b)),
        (Value::Map(x), Value::Map(y)) => {
            x.len() == y.len() && x.iter().all(|(k, v)| y.get(k).map_or(false, |v2| value_eq(v, v2)))
        }
        _ => false,
    }
}

fn interpolate_str(s: &str, env: &Env) -> String {
    let mut out = String::new();
    let mut i = 0;
    let bytes = s.as_bytes();
    while i < bytes.len() {
        if bytes[i] == b'{' {
            let start = i + 1;
            let mut end = start;
            while end < bytes.len() && bytes[end] != b'}' {
                end += 1;
            }
            if end < bytes.len() {
                let var_name = std::str::from_utf8(&bytes[start..end]).unwrap_or("").trim();
                if let Some(v) = env.borrow().get(var_name) {
                    out.push_str(&v.to_string());
                } else {
                    out.push_str(&s[start..=end]);
                }
                i = end + 1;
                continue;
            }
        }
        out.push(bytes[i] as char);
        i += 1;
    }
    out
}
