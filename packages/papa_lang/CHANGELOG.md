# Changelog

## [0.2.0] - 2025

### Added

- Stage 2A: .papa DSL compiler
- `papa compile main.papa --target python|typescript`
- `papa validate main.papa`
- `papa init my_project`
- Lexer, parser, validator (stdlib only, no external deps)
- Codegen: Python (papa-lang SDK), TypeScript (@papa-lang/core)
- SwarmAgent, SwarmRunner, ConsensusConfig, HRSConfig for generated code
- Examples: basic_agent, medical_analysis, finance_pipeline

## [0.1.0] - 2025

### Added

- Orchestrator: client for papa-app /orchestrate with papa-guard input validation
- HRSMonitor: interface for logging HRS verdicts
- Types: OrchestrateResult, SwarmResult, HRSVerdict
