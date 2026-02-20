# Changelog

## v0.8.0 — 2026-02-20

### New Modules (Agent Layer)
- `std/voice` — Voice calls (Telnyx), SMS, transcription (Whisper), TTS
- `std/mcp` — MCP Protocol connectors, Composio.dev (email, calendar)
- `std/browser` — Browser automation, web scraping, screenshots
- `std/telegram` — Telegram Bot API, commands, webhooks, inline keyboards
- `std/design` — AI design system: tokens, components, palettes, UI review
- `std/ai` — ai_budget: cost guardrails, daily limits, spending alerts, reports

### Stats
- 18 stdlib modules (was 12)
- 38 new stdlib functions
- 6 new showcases (06-11)

## v0.7.0 — 2026-02-20

### Language Features
- Match expressions now support multi-line blocks (not just single expressions)
- `for i, item in list` — enumerated loops with index variable
- `enum` type definition
- New string methods: contains, starts_with, ends_with, repeat, chars, index_of

### Tests
- New examples/15_v07_features.papa with v0.7 feature tests
