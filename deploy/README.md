# 🚀 PAPA Deploy — Aviation-Grade Deployment DSL

<p align="center">
  <strong>Declarative deployments with DO-178C inspired safety</strong>
</p>

## Overview

PAPA Deploy is a domain-specific language (DSL) for infrastructure deployment, built as a module of the PAPA-Lang ecosystem. It turns declarative `.papa` configuration files into executable deployment scripts with built-in safety guarantees.

### Why PAPA Deploy?

| Traditional DevOps | PAPA Deploy |
|---|---|
| 10+ bash commands per deploy | 1 command: `papa-deploy run deploy.papa` |
| Manual RAM management | Auto-stops containers when RAM low |
| No rollback | Automatic rollback on healthcheck fail |
| Silent failures | Aviation-grade verification at every step |
| No audit trail | Cryptographic deployment log |

## Quick Start

### Installation

```bash
# Clone
git clone ssh://git@64.227.146.129:2222/papa/papa-lang.git
cd papa-lang/deploy

# Make executable
chmod +x papa-deploy

# Symlink to PATH
sudo ln -sf $(pwd)/papa-deploy /usr/local/bin/papa-deploy
```

### Create deploy config

```papa
// my-app.papa
ecosystem "my-app" {
  safety_level: B

  server "prod" {
    host: "10.0.0.1"
    user: "deploy"
    path: "/opt/my-app"
  }

  sync {
    from: local("./")
    to: server("prod")
    exclude: [node_modules, .git, .env]
    method: delta
    verify: checksum
  }

  build {
    engine: docker
    image: "my-app:latest"
    cache: false
    requires_ram: 2GB
  }

  deploy {
    containers: [
      { name: "my-app", port: 3000, network: "app-net" }
    ]
    strategy: recreate
  }

  verify {
    endpoints: [
      { url: "/api/health", expect: 200 }
    ]
  }
}
```

### Deploy

```bash
# Preview what will happen
papa-deploy run my-app.papa --dry-run

# Full deploy
papa-deploy run my-app.papa

# Only sync files
papa-deploy run my-app.papa --sync-only

# Rollback
papa-deploy run my-app.papa --rollback
```

## Architecture

```
.papa file → Parser → Config Dict → Compiler → Shell Script → Execution
                                        ↑
                                  Safety Level
                                  (A/B/C/D)
```

### Safety Levels (DO-178C DAL inspired)

| Level | Name | Sync Verify | Deploy Strategy | Rollback | Audit |
|-------|------|-------------|-----------------|----------|-------|
| **A** | Critical | Dual checksum | Blue-green | Auto | Full cryptographic |
| **B** | Essential | Checksum | Rolling | Auto | Hash log |
| **C** | Standard | Size | Recreate | Manual | Basic log |
| **D** | Dev | None | Recreate | None | None |

## DSL Reference

### Blocks

| Block | Purpose | Required |
|-------|---------|----------|
| `server` | Remote host configuration | ✅ |
| `sync` | File synchronization rules | ✅ |
| `build` | Docker image build config | ✅ |
| `deploy` | Container deployment | ✅ |
| `verify` | Post-deploy verification | Recommended |
| `hooks` | Pre/post lifecycle hooks | Optional |
| `notify` | CWB/Slack notifications | Optional |
| `rollback` | Rollback configuration | Optional |

### Value Types

| Type | Example |
|------|---------|
| String | `"hello"` |
| Number | `42` |
| Boolean | `true`, `false` |
| Duration | `30s`, `5m`, `1h` |
| Size | `2GB`, `512MB` |
| Array | `[a, b, c]` |
| Env ref | `env("KEY") ?? "default"` |
| Block ref | `build.image` |

### CLI Commands

```
papa-deploy compile <file>          Output generated shell script
papa-deploy run <file>              Full deploy pipeline
papa-deploy run <file> --dry-run    Show plan without executing
papa-deploy run <file> --sync-only  Only sync files
papa-deploy run <file> --build-only Only build image
papa-deploy run <file> --rollback   Rollback to previous version
```

## Examples

### PAPA Ecosystem (production)
See `examples/papa-ecosystem.papa` — full config for the PAPA AI platform.

### Minimal
See `examples/minimal.papa` — simplest possible deploy config.

## Roadmap

- [ ] v1.1: Rust-based delta sync (faster than rsync)
- [ ] v1.2: Blue-green deploy strategy
- [ ] v1.3: Canary deploy with traffic splitting
- [ ] v1.4: CWB messenger integration
- [ ] v1.5: Blockchain audit trail
- [ ] v2.0: Native PAPA-Lang compiler (not Python)
- [ ] v2.1: Distributed multi-server deploy
- [ ] v2.2: Kubernetes support

## PAPA-Lang Integration

PAPA Deploy is a module of the PAPA-Lang ecosystem:

```
PAPA-Lang
├── Core Language (Rust compiler)
├── Deploy Module ← this
├── Config Module (app configuration)
├── Test Module (aviation test framework)
└── Doc Module (documentation generator)
```

## License

MURA MENASA FZCO — Proprietary
