# papa-guard

> AI safety middleware for Russian-language AI systems.  
> PII filter (ФЗ-152) + injection guard + cost tracker.

## Install

```bash
pip install papa-guard
```

## Quick Start

```python
from papa_guard import Guard

guard = Guard()
result = guard.check_input("Звоните +7 999 123-45-67 Ивану Петровичу")

print(result.sanitized_text)   # "Звоните [ТЕЛЕФОН] [ФИО]"
print(result.pii_redacted_count)  # 2
print(result.blocked)   # False
```

## Why papa-guard?

| Feature         | papa-guard | presidio | no solution |
|-----------------|------------|----------|-------------|
| Russian PII     | ✅ native  | partial  | ❌          |
| Zero ML deps    | ✅         | ❌       | ✅          |
| Injection guard | ✅         | ❌       | ❌          |
| Cost tracking   | ✅         | ❌       | ❌          |
| ФЗ-152 compliant | ✅        | partial  | ❌          |
| Processing time | <5ms      | ~50ms    | 0ms         |

## Used by

- papa-app (multi-agent AI orchestration)
- papa-lang ecosystem
