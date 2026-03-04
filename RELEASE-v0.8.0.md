# GitHub Release v0.8.0

**How to use:** Go to https://github.com/yrippert-maker/papa-lang/releases/new → Draft new release

---

## Tag

`v0.8.0`

---

## Title

PAPA Lang v0.8.0 — Next-Generation Programming Language

---

## Release Notes

### 🛡️ PAPA Lang v0.8.0

First public release of PAPA Lang — a programming language designed to eliminate entire categories of bugs by design.

### Key Features

- **No null/undefined** — `maybe` type replaces null with explicit handling
- **Secret type** — passwords and tokens are automatically redacted in logs, stack traces, and string interpolation
- **Immutable by default** — `mut` keyword required for mutable variables
- **One equality operator** — `==` for comparison, `=` for assignment. No `===` confusion
- **Clean syntax** — indentation-based, no semicolons, no curly braces
- **Built-in HTTP server** — `serve on port 8200` with route definitions
- **Built-in ORM** — `model User` with CRUD operations
- **25 stdlib modules** — including AI routing, blockchain audit trail, voice programming, Telegram bot, browser automation

### What's Included

- Python interpreter (`papa.py`)
- Rust backend (compilation target)
- Interactive REPL
- Test runner
- 9 example programs
- Full language specification (SPEC.md)
- 25 standard library modules

### Quick Start

```bash
git clone https://github.com/yrippert-maker/papa-lang.git
cd papa-lang
python3 papa.py run examples/05_full_demo.papa
python3 papa.py repl
```

### License

MIT — Mura Menasa FZCO, Dubai
