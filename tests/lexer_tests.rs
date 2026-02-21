//! Lexer unit tests.

use papa_lang::lexer::{Scanner, TokenKind};

#[test]
fn scan_hello_pl() {
    let source = r#"
let name: str = "PAPA"
fn greet(n: str) -> str {
    "Hello!"
}
"#;
    let mut scanner = Scanner::new(source);
    let tokens = scanner.scan_all();

    let kinds: Vec<_> = tokens.iter().map(|t| &t.kind).collect();
    assert!(kinds.contains(&&TokenKind::Let));
    assert!(kinds.contains(&&TokenKind::Fn));
    assert!(kinds.contains(&&TokenKind::Str));
}
