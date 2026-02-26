# RFC-0002: .papa as KYA Artifact

- **Status:** Proposed
- **Authors:** papa-lang contributors
- **Created:** 2025
- **Discussion:** [git.papa-ai.ae/papa/papa-lang](https://git.papa-ai.ae/papa/papa-lang)

---

## Abstract

This RFC proposes treating `.papa` source files as **KYA (Know Your Agent)** artifacts. A `.papa` file declares an AI agent’s safety configuration—model, guard level, HRS threshold, memory, retrieval, HRS engine, and observability. By producing a KYA artifact (hash, metadata, and optional attestation) from compiled `.papa` definitions, operators and auditors can verify which safety properties an agent was built with, who issued it, and when it expires. This supports compliance, audit trails, and trust in multi-agent AI systems.

---

## Motivation

### 1. Problem

Deployed AI agents lack a portable, verifiable record of their safety configuration. Auditors cannot easily confirm which hallucination thresholds, guard levels, or PII settings were applied at build time.

### 2. Current State

- papa-lang compiles `.papa` to Python/TypeScript.
- No standard format exists for exporting or verifying agent definitions as attestable artifacts.

### 3. Solution

Introduce KYA artifact generation and verification. A KYA artifact binds:
- Agent definition (name, model, guard, hrs_threshold, memory, retrieval, hrs_engine, observability)
- Source reference (e.g., .papa path or content hash)
- Issuer and TTL
- Optional signature/attestation

---

## Specification Summary

### KYA Artifact Fields

| Field          | Description                                      |
|----------------|--------------------------------------------------|
| agent          | Agent definition (name, model, guard, hrs_threshold, memory, retrieval, hrs_engine, observability) |
| source         | Source file path or content identifier           |
| issued_by      | Issuing party identifier                         |
| issued_at      | ISO 8601 timestamp                                |
| ttl_days       | Time-to-live in days (expiry)                     |
| expires_at     | Computed expiry timestamp                         |
| version        | papa-lang KYA format version                     |

### API (Python)

- `generate_kya(agent, source, issued_by, ttl_days)` — build KYA artifact dict
- `export_kya(kya_dict, path)` — write KYA to file (e.g., JSON)
- `verify_kya(kya_dict)` — validate structure and expiry

---

## Open Questions (for Community Feedback)

**Q1:** Should KYA support digital signatures (e.g., Ed25519) in v0.3?

**Q2:** Should `source` include content hash of the `.papa` file for integrity?

**Q3:** Should KYA artifacts be embedded in compiled output or stored separately?

---

## Governance

- **RFC process:** Submit PR to `docs/rfc/` with format `RFC-NNNN-title.md`
- **Review period:** 30 days minimum
- **Acceptance:** 2 maintainer approvals + no blocking objections
