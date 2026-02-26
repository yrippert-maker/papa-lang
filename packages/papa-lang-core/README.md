# @papa-lang/core

TypeScript SDK for the papa-lang AI-native ecosystem: orchestrate, RAG, and guard types.

## Install

```bash
npm install @papa-lang/core
```

## Usage

```ts
import { PapaClient } from "@papa-lang/core";

const client = new PapaClient("https://api.papa-ai.ae", process.env.PAPA_API_KEY);

const result = await client.orchestrate("What is papa-lang?");
console.log(result.response, result.verdict);

const rag = await client.ragSearch("documentation");
console.log(rag.context);
```

## Exports

- `PapaClient` — HTTP client for `orchestrate()` and `ragSearch()`
- Types: `OrchestrateResult`, `SwarmResult`, `HRSScore`, `GuardResult`, etc.

## License

MIT
