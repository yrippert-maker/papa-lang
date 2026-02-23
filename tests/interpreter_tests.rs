//! Interpreter integration tests.

use papa_lang::interpreter::Evaluator;
use papa_lang::lexer::Scanner;
use papa_lang::parser::Parser;

fn run(source: &str) -> Result<papa_lang::interpreter::Value, String> {
    let mut scanner = Scanner::new(source);
    let tokens = scanner.scan_all();
    let mut parser = Parser::new(tokens);
    let program = parser.parse();
    let mut evaluator = Evaluator::new();
    evaluator.eval_program(&program)
}

#[test]
fn test_arithmetic() {
    let result = run("let x = 10 + 20").unwrap();
    // Last statement is Let which returns the assigned value
    assert!(matches!(result, papa_lang::interpreter::Value::Int(30)));
    let result = run(r#"let a = 5
let b = 3
let c = a + b
print(c)"#);
    assert!(result.is_ok());
}

#[test]
fn test_string_concat() {
    let result = run(r#"
let a = "Hello"
let b = "World"
let c = a + " " + b
print(c)
"#);
    assert!(result.is_ok());
}

#[test]
fn test_function() {
    let result = run(r#"
fn add(x: int, y: int) -> int {
    x + y
}
let z = add(1, 2)
print(z)
"#);
    assert!(result.is_ok());
}

#[test]
fn test_match() {
    let result = run(r#"
let x = 42
match x {
  0 => { print("zero") }
  1..10 => { print("small") }
  10..100 => { print("medium") }
  _ => { print("large") }
}
"#);
    assert!(result.is_ok(), "match failed: {:?}", result.err());
}

#[test]
fn test_match_ok_err() {
    let result = run(r#"
let res = ok("hello")
match res {
  Ok(s) => { print(s) }
  Err(e) => { print("error") }
}
"#);
    assert!(result.is_ok(), "match Ok/Err failed: {:?}", result.err());
}

#[test]
fn test_pipeline() {
    let result = run(r#"
fn double(x) { x * 2 }
let y = 5 |> double()
print(y)
"#);
    assert!(result.is_ok());
}
