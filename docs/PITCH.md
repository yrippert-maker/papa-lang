# papa-lang: Linux Foundation AI & Data Foundation Proposal

---

## Project Summary

papa-lang is an open-source declarative DSL for AI safety configuration. Developers write `.papa` files describing agent safety constraints; the compiler generates production-ready Python or TypeScript code.

---

## Problem Statement

The AI industry lacks a standard for expressing safety properties. Hallucinations cause significant damages annually. No portable format exists for:

- HRS (Hallucination Risk Score) thresholds
- PII filtering requirements
- Consensus requirements in multi-agent systems

---

## Solution

papa-lang provides:

1. **A grammar** for AI safety declarations — agents, swarms, pipelines
2. **A reference compiler** — Python and TypeScript targets
3. **HRS** — a measurable safety metric (0.0–1.0)
4. **Guard levels** — strict, standard, minimal (mapped to thresholds)

---

## Alignment with LF AI&D Mission

- **Open governance:** RFC process, community-driven specification
- **Vendor neutral:** No dependency on specific AI provider (works with any model)
- **Complementary to existing LF projects:**
  - **Trusted AI** — papa-lang adds measurable safety metrics
  - **OpenSSF** — papa-lang adds supply chain safety for AI artifacts

---

## Current State

| Component | Status |
|-----------|--------|
| Python package | `pip install papa-lang==0.2.0` (PyPI) |
| TypeScript package | `npm install @papa-lang/core@0.1.0` |
| CLI | `papa compile`, `papa validate`, `papa init` |
| Tests | 8 passing |
| Production use | papa-ecosystem (10 modules) |

---

## Governance Proposal

- **Stage:** Sandbox (initial LF stage)
- **Maintainers:** 1 founding maintainer (open to community)
- **License:** Apache 2.0
- **Code of Conduct:** Contributor Covenant
- **RFC process:** Documented in `docs/rfc/`

---

## Roadmap to v1.0

| Quarter | Milestone |
|---------|-----------|
| Q1 2026 | v0.3 — import, JSON/YAML targets, tool definitions |
| Q2 2026 | v0.4 — conditional routing, A/B declarations |
| Q3 2026 | v1.0 — stability guarantee + conformance test suite |
| Q4 2026 | LF Incubation stage application |

---

## Why Now

- **EU AI Act (2024):** Requires documented AI safety measures. papa-lang provides machine-readable compliance artifacts.
- **NIST AI RMF:** papa-lang maps to GOVERN and MEASURE functions.
- **MCP adoption (2024):** Proved market appetite for AI standards.

---

## References

- [SPEC.md](../SPEC.md) — Language specification
- [RFC-0001](rfc/RFC-0001-papa-lang-specification.md) — Specification RFC
- [PyPI](https://pypi.org/project/papa-lang/) — Python package
- [npm](https://www.npmjs.com/package/@papa-lang/core) — TypeScript package
