# Contributing to PAPA Lang

## Quick Start

```bash
git clone <repo>
cd papa-lang
python papa.py test          # Run all tests
python papa.py run examples/hello.papa
```

## Project Structure

```
papa-lang/
├── papa.py              # CLI entry point
├── src/
│   ├── lexer.py         # Tokenizer: source → tokens
│   ├── parser.py        # Parser: tokens → AST
│   ├── ast_nodes.py     # AST node definitions
│   ├── interpreter.py   # Main interpreter + built-ins
│   ├── evaluator.py     # Expression evaluation (mixin)
│   ├── executor.py      # Statement execution (mixin)
│   ├── environment.py   # Variable scope / environment
│   ├── type_checker.py  # Type checking
│   └── stdlib_core.py   # Core stdlib (Python FFI)
├── std/                 # PAPA stdlib declarations (.papa)
├── tests/               # Test suite (60+ tests)
├── examples/            # Example programs
└── docs/                # Documentation
```

## How to Add a New Stdlib Module

1. Create `std/mymodule.papa` with function declarations
2. Create Python implementation in `src/` (or `src/stdlib/`)
3. Register built-in functions in interpreter
4. Add tests in `tests/`
5. Update `docs/SPECIFICATION.md`

## How to Add a New AST Node

1. Define in `src/ast_nodes.py`
2. Add parsing in `src/parser.py`
3. Add keyword in `src/lexer.py` if needed
4. Add execution in `src/executor.py` or evaluation in `src/evaluator.py`
5. Add tests
6. Update grammar in `docs/SPECIFICATION.md`

## Running Tests

```bash
python papa.py test          # Quick
make test                    # Verbose
make coverage                # With coverage report
```

All 60 tests must pass before merging any changes.
