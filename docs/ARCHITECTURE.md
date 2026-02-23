# PAPA Lang Architecture

## Pipeline

```
Source (.papa) → Lexer → Tokens → Parser → AST → Interpreter → Output
                                                    ├── Evaluator (expressions)
                                                    ├── Executor (statements)
                                                    ├── Stdlib (Python FFI)
                                                    └── HTTP Server
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Immutability by default (`let`) | Prevents accidental mutation |
| `secret` type | Auto-redacted in output/logs — unique feature |
| `maybe` instead of null | Like Rust's Option, with `??` fallback |
| Tree-walking interpreter | Simple, correct; bytecode VM planned |
| Python FFI for stdlib | Leverage Python ecosystem |

## Components

### Lexer (`src/lexer.py`)
Tokenizes source code. 87 keywords, supports string interpolation, multi-line strings.

### Parser (`src/parser.py`)
Recursive descent. Produces AST nodes defined in `src/ast_nodes.py`.

### Interpreter (`src/interpreter.py`)
Composes EvaluatorMixin + ExecutorMixin. Manages environment, routes, built-in functions.

### Environment (`src/environment.py`)
Lexical scoping with parent chain. Tracks mutability (`let` vs `mut`).

### Type System
- Built-in: int, float, str, bool, list, map, nothing
- Special: secret (redacted), maybe (nullable wrapper)
- Annotations exist but are not fully enforced at runtime

## Known Limitations

| Limitation | Plan |
|-----------|------|
| Tree-walking speed | Bytecode VM (Phase 4) |
| No closures | First-class functions (Phase 4) |
| 87 keywords | Reduce to ~50 |
| Type checking incomplete | Full runtime checks (Phase 4) |
| No formal GC | Persistent data structures |
