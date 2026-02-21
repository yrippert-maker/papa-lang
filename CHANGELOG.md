# Changelog

## v0.8.1 — 2026-02-21

### Bugfixes
- 60/60 tests passing (was 56/60)
- `std/ai_router` — fallback response when no API keys (test mode)
- `std/swarm` — convert PapaMap/PapaList in create_with_agents
- `std/verify` — convert PapaMap spec to plain dict for analysis
- `std/voice_prog` — return Maybe.none() for unknown commands
- Root cause: PapaMap/PapaList types not unwrapped in std module functions

### Documentation
- README: 18→25 std modules, added all Wave 2 & Wave 3 modules table

## v0.8.0 — 2026-02-20

### New Modules — Wave 2 (Agent Layer)
- `std/orchestrator` — AI safety layer: review, verify, autofix cycle
- `std/ai_router` — Smart AI model routing (Claude, GPT, Gemini)
- `std/evolve` — Self-evolving code analysis
- `std/swarm` — Multi-agent swarm: consensus, delegation
- `std/gemini` — Google Gemini integration
- `std/guard` — AI guardrails: PII detection, injection prevention, cost control
- `std/infra` — Infrastructure management

### New Modules — Wave 3 (Enterprise)
- `std/studio` — Development studio: analyze, structure, estimate
- `std/docs` — Document generation: brand, logo, templates
- `std/cwb` — CWB Mobile Assistant: tasks, ideas, commands
- `std/chain` — Blockchain audit trail (GDPR, 152-ФЗ, HIPAA)
- `std/verify` — Vericoding: AI-verified code + formal proofs
- `std/voice_prog` — Voice programming: code by speaking

### New Modules (Agent Layer)
- `std/voice` — Voice calls (Telnyx), SMS, transcription (Whisper), TTS
- `std/mcp` — MCP Protocol connectors, Composio.dev (email, calendar)
- `std/browser` — Browser automation, web scraping, screenshots
- `std/telegram` — Telegram Bot API, commands, webhooks, inline keyboards
- `std/design` — AI design system: tokens, components, palettes, UI review
- `std/ai` — ai_budget: cost guardrails, daily limits, spending alerts, reports

### Stats
- 25 stdlib modules (was 18)
- 70+ stdlib functions across all modules
- 20 showcases (06-17 + demos)

## v0.7.0 — 2026-02-20

### Language Features
- Match expressions now support multi-line blocks (not just single expressions)
- `for i, item in list` — enumerated loops with index variable
- `enum` type definition
- New string methods: contains, starts_with, ends_with, repeat, chars, index_of

### Tests
- New examples/15_v07_features.papa with v0.7 feature tests
