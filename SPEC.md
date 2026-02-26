# papa-lang Language Specification

## Version: 0.2 | Status: Draft | Date: 2025

---

## 1. Introduction

### 1.1 Goals

papa-lang is a declarative domain-specific language for configuring AI agent safety properties. It enables developers to express hallucination thresholds, PII filtering, consensus requirements, and module routing in a single, portable format.

### 1.2 Non-Goals

- papa-lang is not a general-purpose programming language
- papa-lang does not execute AI models directly
- papa-lang does not replace orchestration runtimes (it configures them)

### 1.3 Relationship to MCP

papa-lang is complementary to MCP (Model Context Protocol). MCP standardizes how AI models connect to tools; papa-lang standardizes how AI systems declare safety constraints. Both can be used together.

### 1.4 Design Principles

- **Readability over brevity** — explicit configuration over terse syntax
- **Explicit safety over implicit defaults** — hrs_threshold and guard levels are always visible
- **Target-agnostic** — compiles to Python, TypeScript, and planned: JSON, YAML
- **Fail-safe** — unknown properties raise errors, not silent warnings

---

## 2. Lexical Structure

### 2.1 Character Set

UTF-8.

### 2.2 Whitespace

Whitespace (spaces, tabs, newlines) is ignored outside string literals.

### 2.3 Comments

- Single-line: `//` to end of line
- Single-line: `#` to end of line (alternative)

### 2.4 Keywords (reserved)

`agent` `swarm` `tool` `pipeline` `import`

### 2.5 Identifiers

```
[a-zA-Z_][a-zA-Z0-9_\-\.]*
```

Identifiers may contain hyphens and dots (e.g. `gemini-1.5-pro`).

### 2.6 Literals

| Type | Syntax | Example |
|------|--------|---------|
| String | `'value'` or `"value"` | `'claude-3-sonnet'` |
| Float | `0.15` (leading zero required for &lt;1) | `0.10` |
| Integer | `4` | `4` |
| Fraction | `N/M` (consensus syntax only) | `4/7` |
| Boolean | `enabled` \| `disabled` | `enabled` |

**Note:** No escape sequences in strings in v0.2.

---

## 3. Grammar (EBNF)

```ebnf
program       = { statement } ;

statement     = agent_def | swarm_def | pipeline_def | import_stmt ;

agent_def     = 'agent' IDENT '{' { agent_prop } '}' ;

agent_prop    = 'model' ':' ( STRING | IDENT )
              | 'guard' ':' guard_level
              | 'hrs_threshold' ':' FLOAT
              | 'memory' ':' bool_lit
              ;

guard_level   = 'strict' | 'standard' | 'minimal' ;

swarm_def     = 'swarm' IDENT '{' { swarm_prop } '}' ;

swarm_prop    = 'agents' ':' '[' agent_list ']'
              | 'consensus' ':' FRACTION
              | 'anchor' ':' anchor_type
              | 'pii' ':' pii_mode
              | 'hrs_max' ':' FLOAT
              ;

agent_list    = IDENT { ',' IDENT } ;

anchor_type   = 'blockchain' | 'hash' | 'none' ;

pii_mode      = 'filter' | 'mask' | 'none' ;

pipeline_def  = 'pipeline' IDENT '{' { pipeline_prop } '}' ;

pipeline_prop = 'route' ':' route_type
              | 'fallback' ':' route_type
              | 'module' ':' ( STRING | IDENT )
              ;

route_type    = 'orchestrator' | 'single' | 'swarm' ;

bool_lit      = 'enabled' | 'disabled' ;

(* import_stmt planned for v0.3 *)
```

---

## 4. Semantic Rules

### 4.1 Agent Resolution

Agents referenced in `swarm.agents` **MUST** be defined in the same program. Violation raises `SEM001: Agent "X" not defined`.

### 4.2 HRS Constraints

`hrs_threshold` (per agent) and `hrs_max` (per swarm) **MUST** be in the range `[0.0, 1.0]`. Violation raises `SEM002: hrs_threshold must be 0.0-1.0`.

### 4.3 Consensus Validity

For consensus fraction `N/M`, `N` (required) **MUST** be less than or equal to `M` (of). Violation raises `SEM003: consensus N/M is invalid`.

### 4.4 Guard Levels

| Level | PASS if HRS &lt; | BLOCK if HRS ≥ | Use Case |
|-------|-----------------|----------------|----------|
| strict | 0.10 | 0.20 | Critical modules (health, finance, legal) |
| standard | 0.15 | 0.30 | Default |
| minimal | 0.25 | 0.50 | Internal tools |

---

## 5. Standard Library Modules

| Module | Domain | Default Guard |
|--------|--------|---------------|
| papa-life | Health | strict |
| papa-finance | Financial | strict |
| papa-legal | Legal | strict |
| papa-devops | Infrastructure | standard |
| papa-docs | Documentation | standard |
| papa-ai-hub | AI management | standard |

---

## 6. Compilation Targets

| Target | Output | Runtime |
|--------|--------|---------|
| python | `.py` | papa-lang SDK (`pip install papa-lang`) |
| typescript | `.ts` | @papa-lang/core (`npm install @papa-lang/core`) |
| json | JSON schema (planned v0.3) | — |
| yaml | YAML config (planned v0.3) | — |

---

## 7. HRS (Hallucination Risk Score) Definition

**HRS ∈ [0.0, 1.0]** — estimated probability that an AI response contains fabricated or unverifiable information.

**Measurement factors:**
- Semantic consistency
- Source grounding
- Confidence calibration

**Verdict mapping:**

| Condition | Verdict | Action |
|-----------|---------|--------|
| HRS &lt; threshold | PASS | Response shown to user |
| threshold ≤ HRS &lt; max | WARN | Response shown with warning |
| HRS ≥ max | BLOCK | Response hidden, user sees error |

---

## 8. Versioning

- Spec version: `MAJOR.MINOR` (no patch)
- `.papa` files **SHOULD** include: `// @papa-lang v0.2`
- Breaking changes require MAJOR bump

---

## Appendix A: Complete Example

```papa
# medical_analysis.papa
agent synthesis {
  model: gemini-1.5-pro
  guard: strict
  hrs_threshold: 0.10
  memory: enabled
}

agent research {
  model: claude-3-sonnet
  guard: standard
  hrs_threshold: 0.10
}

swarm medical_team {
  agents: [synthesis, research]
  consensus: 4/7
  anchor: blockchain
  pii: filter
  hrs_max: 0.15
}

pipeline main {
  route: orchestrator
  fallback: single
  module: papa-life
}
```

---

## Appendix B: Error Reference

| Code | Category | Description |
|------|----------|-------------|
| LEX001-LEX999 | Lexer | Tokenization errors |
| PARSE001-PARSE999 | Parser | Syntax errors |
| SEM001 | Semantic | Agent not defined |
| SEM002 | Semantic | hrs_threshold out of range |
| SEM003 | Semantic | Invalid consensus fraction |

---

## Appendix C: Changelog

- **0.1** — Initial DSL (agents only)
- **0.2** — Swarms, pipelines, consensus, PII, compilation targets (Python, TypeScript)
