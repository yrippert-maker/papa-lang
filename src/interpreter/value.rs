//! Runtime values for PL interpreter.

use std::collections::HashMap;
use std::fmt;

/// A value at runtime.
#[derive(Debug, Clone)]
pub enum Value {
    Int(i64),
    Float(f64),
    Str(String),
    Bool(bool),
    None,
    /// List/array
    List(Vec<Value>),
    /// Map/object
    Map(HashMap<String, Value>),
    /// User-defined function (name, param_names, body — captured in Evaluator)
    Function {
        name: String,
        params: Vec<String>,
        body: Vec<crate::parser::ast::Stmt>,
    },
    /// Built-in function
    Builtin(String),
    /// Object/record (legacy, prefer Map)
    Object(HashMap<String, Box<Value>>),
    /// Result::Ok(value)
    Ok(Box<Value>),
    /// Result::Err(value)
    Err(Box<Value>),
}

impl Value {
    pub fn as_str(&self) -> Option<&str> {
        match self {
            Value::Str(s) => Some(s),
            _ => None,
        }
    }

    pub fn as_int(&self) -> Option<i64> {
        match self {
            Value::Int(i) => Some(*i),
            _ => None,
        }
    }

    pub fn as_map(&self) -> Option<&HashMap<String, Value>> {
        match self {
            Value::Map(m) => Some(m),
            _ => None,
        }
    }

    pub fn as_list(&self) -> Option<&Vec<Value>> {
        match self {
            Value::List(l) => Some(l),
            _ => None,
        }
    }

    pub fn is_truthy(&self) -> bool {
        match self {
            Value::Bool(b) => *b,
            Value::None => false,
            Value::Int(0) => false,
            Value::Float(f) => *f != 0.0,
            Value::Str(s) => !s.is_empty(),
            Value::List(l) => !l.is_empty(),
            Value::Map(m) => !m.is_empty(),
            Value::Err(_) => false,
            _ => true,
        }
    }

    pub fn type_name(&self) -> &'static str {
        match self {
            Value::Int(_) => "int",
            Value::Float(_) => "float",
            Value::Str(_) => "str",
            Value::Bool(_) => "bool",
            Value::None => "none",
            Value::List(_) => "list",
            Value::Map(_) => "map",
            Value::Object(_) => "object",
            Value::Function { .. } => "fn",
            Value::Builtin(_) => "builtin",
            Value::Ok(_) => "ok",
            Value::Err(_) => "err",
        }
    }

    pub fn as_ok(&self) -> Option<&Value> {
        match self {
            Value::Ok(v) => Some(v),
            _ => None,
        }
    }

    pub fn as_err(&self) -> Option<&Value> {
        match self {
            Value::Err(v) => Some(v),
            _ => None,
        }
    }

    /// Convert to serde_json for storage/API
    pub fn to_json_string(&self) -> String {
        serde_json::to_string(&self.to_json()).unwrap_or_else(|_| "null".into())
    }

    pub fn to_json(&self) -> serde_json::Value {
        match self {
            Value::Int(i) => serde_json::Value::Number((*i).into()),
            Value::Float(f) => serde_json::Number::from_f64(*f)
                .map(serde_json::Value::Number)
                .unwrap_or(serde_json::Value::Null),
            Value::Str(s) => serde_json::Value::String(s.clone()),
            Value::Bool(b) => serde_json::Value::Bool(*b),
            Value::None => serde_json::Value::Null,
            Value::List(l) => {
                serde_json::Value::Array(l.iter().map(|v| v.to_json()).collect())
            }
            Value::Map(m) => {
                let obj: serde_json::Map<String, serde_json::Value> = m
                    .iter()
                    .map(|(k, v)| (k.clone(), v.to_json()))
                    .collect();
                serde_json::Value::Object(obj)
            }
            Value::Object(m) => {
                let obj: serde_json::Map<String, serde_json::Value> = m
                    .iter()
                    .map(|(k, v)| (k.clone(), v.to_json()))
                    .collect();
                serde_json::Value::Object(obj)
            }
            Value::Function { name, .. } => serde_json::json!({"fn": name}),
            Value::Builtin(name) => serde_json::json!({"builtin": name}),
            Value::Ok(v) => serde_json::json!({"ok": v.to_json()}),
            Value::Err(v) => serde_json::json!({"err": v.to_json()}),
        }
    }

    pub fn from_json(j: serde_json::Value) -> Self {
        match j {
            serde_json::Value::Null => Value::None,
            serde_json::Value::Bool(b) => Value::Bool(b),
            serde_json::Value::Number(n) => {
                if let Some(i) = n.as_i64() {
                    Value::Int(i)
                } else {
                    Value::Float(n.as_f64().unwrap_or(0.0))
                }
            }
            serde_json::Value::String(s) => Value::Str(s),
            serde_json::Value::Array(a) => {
                Value::List(a.into_iter().map(Value::from_json).collect())
            }
            serde_json::Value::Object(o) => {
                if o.len() == 1 {
                    if let Some(v) = o.get("ok").cloned() {
                        return Value::Ok(Box::new(Value::from_json(v)));
                    }
                    if let Some(v) = o.get("err").cloned() {
                        return Value::Err(Box::new(Value::from_json(v)));
                    }
                }
                let m: HashMap<String, Value> = o
                    .into_iter()
                    .map(|(k, v)| (k, Value::from_json(v)))
                    .collect();
                Value::Map(m)
            }
        }
    }
}

impl fmt::Display for Value {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Value::Int(i) => write!(f, "{}", i),
            Value::Float(x) => write!(f, "{}", x),
            Value::Str(s) => write!(f, "{}", s),
            Value::Bool(b) => write!(f, "{}", b),
            Value::None => write!(f, "none"),
            Value::List(l) => {
                write!(f, "[")?;
                for (i, v) in l.iter().enumerate() {
                    if i > 0 {
                        write!(f, ", ")?;
                    }
                    write!(f, "{}", v)?;
                }
                write!(f, "]")
            }
            Value::Map(m) => {
                write!(f, "{{")?;
                for (i, (k, v)) in m.iter().enumerate() {
                    if i > 0 {
                        write!(f, ", ")?;
                    }
                    write!(f, "{}: {}", k, v)?;
                }
                write!(f, "}}")
            }
            Value::Function { name, .. } => write!(f, "<fn {}>", name),
            Value::Builtin(name) => write!(f, "<builtin {}>", name),
            Value::Object(_) => write!(f, "<object>"),
            Value::Ok(v) => write!(f, "ok({})", v),
            Value::Err(v) => write!(f, "err({})", v),
        }
    }
}
