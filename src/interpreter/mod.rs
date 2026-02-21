//! Tree-walking interpreter for PAPA Lang (dev mode).

mod builtins;
mod evaluator;
mod value;

pub use evaluator::{Environment, Evaluator};
pub use value::Value;
