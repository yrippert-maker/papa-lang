# PAPA Lang Specification v0.8

## 1. Lexical Structure

### 1.1 Keywords
mut, if, else, match, some, none, for, in, loop, break, return, fail, and, or, not, is, as, true, false, type, model, route, serve, on, port, test, assert, say, log, fn, do, input, auth, required, guard, exists, async, task, every, when, enum, import, from, maybe, list, map, set, secret, sensitive, has, many, unique, where, order, by, limit, repeat, times, wait, try, catch, seconds, minutes, hours, days

### 1.2 Operators
+, -, *, /, %, ==, !=, <, >, <=, >=, and, or, not, ->, =>, ??, |>, .., ?., ?

### 1.3 Literals
- Integer: `42`, `0xFF`, `0b1010`, `0o17`
- Float: `3.14`, `1e10`, `1.5e-3`
- String: `"hello"`, `"hello {name}"` (interpolation), `"""multiline"""`
- Boolean: `true`, `false`
- Nothing: `nothing`

### 1.4 Comments
- Single-line: `// comment`
- Multi-line: `/* comment */`

## 2. Grammar (EBNF)

```
program        = { statement } ;
statement      = assignment | reassignment | say_stmt | log_stmt | if_stmt
               | match_stmt | for_loop | loop_stmt | return_stmt | fail_stmt
               | assert_stmt | try_catch | fn_def | type_def | model_def
               | enum_def | route_def | serve_def | test_def | task_def | every_def
               | import_stmt | from_import | expression ;

assignment     = "mut"? IDENT (":" type)? "=" expression ;
reassignment   = IDENT "=" expression ;

if_stmt        = "if" expression block { "elif" expression block } ["else" block] ;
for_loop       = "for" IDENT "in" expression block ;
match_stmt     = "match" expression "{" { match_arm } "}" ;

fn_def         = "fn" IDENT "(" [ params ] ")" [ "->" type ] block ;
params         = param { "," param } ;
param          = IDENT [ ":" type ] [ "=" expression ] ;

block          = "{" { statement } "}" ;

expression     = assignment_expr | pipe_expr | ternary | or_expr | ... ;
```

## 3. Type System

### 3.1 Built-in Types
- int, float, str, bool, list, map, nothing
- secret — auto-redacted in output/logs
- maybe — wraps value or nothing (replaces null)

### 3.2 Mutability
- `let`/default bindings: immutable
- `mut` creates mutable binding
- Reassignment via `=` for mutable bindings

## 4. Standard Library

Modules: math, string, json, http, fs, time, voice, mcp, browser, telegram, ai, design, orchestrator, docs, studio, cwb, guard, ai_router, evolve, swarm, infra, gemini, verify, chain, voice_prog

## 5. Built-in Functions

ask, env, assert_true, assert_false, and all stdlib module exports.
