# RFC-0001: papa-lang Declarative AI Safety Language

- **Status:** Draft
- **Authors:** papa-lang contributors
- **Created:** 2025
- **Discussion:** [git.papa-ai.ae/papa/papa-lang](https://git.papa-ai.ae/papa/papa-lang)

---

## Abstract

papa-lang is a declarative domain-specific language for configuring AI agent safety properties. It addresses the lack of standardized formats for expressing hallucination thresholds, PII filtering, consensus requirements, and module routing in multi-agent AI systems. This RFC proposes the initial specification and invites community feedback.

---

## Motivation

### 1. Problem

AI safety configuration is scattered, implicit, and fragile. Teams encode safety constraints in ad-hoc YAML, JSON, or Python, leading to inconsistency and runtime failures.

### 2. Current State

Every team writes custom configuration. There is no portable format for:

- Hallucination Risk Score (HRS) thresholds
- PII filtering modes (filter, mask, none)
- Consensus requirements (e.g., 4 of 7 agents must agree)
- Guard levels (strict, standard, minimal)

### 3. Cost

Hallucinations in production cause real harm: misinformation, compliance violations, and loss of user trust. Declaring safety constraints at design time reduces these risks.

### 4. Solution

papa-lang enables developers to declare safety constraints in `.papa` files. The compiler generates production-ready code for Python, TypeScript, and planned targets.

---

## Comparison with Existing Approaches

| Approach | Declarative | Safety-first | Compilable | Open |
|----------|-------------|--------------|------------|------|
| YAML config | Yes | No | No | Yes |
| LangChain | No | No | No | Yes |
| MCP | Yes | No | No | Yes |
| **papa-lang** | Yes | Yes | Yes | Yes |

---

## Specification Summary

**Reference:** [SPEC.md](../../SPEC.md) (in this repository)

### Key Constructs

- **agent** — Defines an AI agent with model, guard level, HRS threshold, and memory
- **swarm** — Groups agents with consensus, PII, and anchor settings
- **pipeline** — Defines routing (orchestrator, single, swarm) and module

### Key Safety Primitives

- `hrs_threshold` — Per-agent hallucination threshold (0.0–1.0)
- `guard` — Level: strict, standard, minimal
- `consensus` — Fraction N/M for swarm agreement
- `pii` — PII handling: filter, mask, none

---

## Reference Implementation

```
pip install papa-lang==0.2.0
```

- **Compiler:** `papa compile`, `papa validate`, `papa init`
- **Targets:** Python, TypeScript
- **Tests:** 8 passing (lexer, parser, validator, codegen)

---

## Open Questions (for Community Feedback)

**Q1:** Should HRS be a mandatory field or optional with defaults?

**Q2:** Should papa-lang support custom guard levels beyond strict/standard/minimal?

**Q3:** Should the compiler support inline expressions (e.g. `hrs_threshold: 0.05 * 2`)?

**Q4:** What additional compilation targets are needed? (Go, Rust, Java?)

**Q5:** Should HRS definition be standardized as a separate sub-RFC?

---

## Governance

- **RFC process:** Submit PR to `docs/rfc/` with format `RFC-NNNN-title.md`
- **Review period:** 30 days minimum
- **Acceptance:** 2 maintainer approvals + no blocking objections
- **Breaking changes:** New RFC required

---

## Roadmap

- **v0.3:** import statements, JSON/YAML targets, tool definitions
- **v0.4:** conditional routing, A/B testing declarations
- **v1.0:** stability guarantee, conformance test suite
- **LF:** Linux Foundation AI & Data Foundation submission
