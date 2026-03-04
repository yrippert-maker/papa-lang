# Reddit — r/ProgrammingLanguages

**URL:** https://www.reddit.com/r/ProgrammingLanguages/submit  
**Flair:** "Language announcement"

---

## Title

PAPA Lang — new language that eliminates null, auto-redacts secrets, and is immutable by default

---

## Body

Hey everyone! I've been working on a new programming language called **PAPA Lang** and just published v0.8.0.

**The core idea:** I analyzed pain points across 10 popular languages and designed PAPA to eliminate entire categories of bugs by design, not by convention.

**What makes it different:**

- **No null/undefined** — there's a `maybe` type. `user = some("admin")` then `name = user ?? "anonymous"`
- **Secret type** — `password = secret("SuperSecret123!")` → any attempt to print it shows `***REDACTED***`. Works in string interpolation, logs, stack traces.
- **Immutable by default** — you need `mut` to make something mutable. `server = "papa-ai.ae"` is locked.
- **One equality** — `==` compares, `=` assigns. No `===` vs `==` debates.
- **Built-in HTTP** — `serve on port 8200` with `route GET "/"` syntax
- **Built-in ORM** — `model User` with `.create()`, `.find()`, `.where()`

**Example:**
```
name = "PAPA"
say "Hello, {name}!"

password = secret("SuperSecret123!")
say "Password: {password}"   // → Password: ***REDACTED***

double(n: int) -> int = n * 2
say double(21)  // → 42
```

Currently implemented as a Python interpreter with a Rust backend in progress. 25 standard library modules including AI routing, blockchain audit trail, and voice programming.

Repo: https://github.com/yrippert-maker/papa-lang

Would love feedback on the language design decisions!
