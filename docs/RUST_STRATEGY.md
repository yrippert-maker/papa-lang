# PAPA Lang — Rust Backend Strategy

## Current State
- **Python**: working interpreter (lexer → parser → AST → tree-walking interpreter)
- **Rust**: standalone HTTP server with SQLite + JWT, NOT connected to PAPA Lang (.pl files)

## Decision: Rust = Future Native Runtime

### Phase 1: Shared Grammar (v0.9)
- Port lexer to Rust (based on SPECIFICATION.md EBNF)
- Port parser to Rust
- Verify Rust parser output matches Python parser on all 60 test cases

### Phase 2: Bytecode Compiler (v1.0)
- Design bytecode format
- Python: AST → bytecode compiler
- Rust: bytecode VM (replaces tree-walking)

### Phase 3: Native Runtime (v1.1+)
- Rust HTTP server becomes PAPA App runtime
- SQLite integration for Model persistence
- Native async for every/task

## Directory Structure

```
papa-lang/
├── src/              # Python interpreter (current)
│   ├── lexer.py
│   ├── parser.py
│   ├── interpreter.py
│   └── ...
├── src/              # Rust (main.rs, etc. — coexists)
│   └── main.rs
├── Cargo.toml
├── spec/             # Shared test cases (both impls must pass)
└── docs/
```

## Action Items
1. Keep Python interpreter as reference implementation
2. New Rust code starts with lexer.rs matching SPECIFICATION.md
3. Share test corpus between Python and Rust
