# PAPA-Lang Deploy DSL — Specification v1.0

## Overview

PAPA Deploy is a declarative DevOps language for aviation-grade deployments.
Built as a module of PAPA-Lang, it compiles to shell scripts with built-in
safety guarantees inspired by DO-178C (Software Considerations in Airborne
Systems and Equipment Certification).

## Design Principles

1. **Declarative** — describe WHAT, not HOW
2. **Atomic** — deploy succeeds completely or rolls back
3. **Auditable** — every action logged with cryptographic hash
4. **RAM-aware** — auto-manages resources on constrained servers
5. **Aviation-grade** — dual verification, checksums, rollback

## Syntax

### Server Block
```papa
server "name" {
  host: "ip_or_domain"
  user: "username"
  port: 22
  key: "~/.ssh/id_rsa"          // optional, default SSH key
  path: "/opt/project"           // remote project root
}
```

### Sync Block
```papa
sync {
  from: local("./")
  to: server("name")
  exclude: [node_modules, .next, .git, .venv, .env, __pycache__]
  method: delta                  // delta (rsync-like) | full | archive
  verify: checksum               // checksum | size | none
  bandwidth: unlimited           // or "10m" for 10 MB/s limit
  compress: true
  timeout: 300s
}
```

### Build Block
```papa
build {
  engine: docker                 // docker | podman | buildah
  image: "name:tag"
  file: "Dockerfile"             // optional, default "Dockerfile"
  context: "."
  args: {
    KEY: "value"
    KEY2: env("ENV_VAR") ?? "fallback"
  }
  cache: false                   // --no-cache flag
  requires_ram: 2GB              // auto-stop heavy containers if free RAM < threshold
  timeout: 600s
}
```

### Deploy Block
```papa
deploy {
  containers: [
    {
      name: "container-name"
      image: build.image          // reference to build block
      port: 3000                  // host:container (3000:3000)
      network: "network-name"
      env_file: ".env"
      restart: "unless-stopped"
      healthcheck: "/api/health"
      healthcheck_timeout: 60s
    }
  ]
  
  strategy: rolling              // rolling | blue-green | canary | recreate
  
  // Services to restart after deploy
  start_after: [
    "papa-api-prod",
    "papa-redis-prod",
    "papa-n8n-prod"
  ]
  
  // Cleanup
  prune_images: true
  prune_containers: true
}
```

### Verify Block
```papa
verify {
  endpoints: [
    { url: "/api/health", expect: 200 },
    { url: "/api/orchestrator/status", expect: 200 },
    { url: "/api/swarm", expect: 401 },    // auth required = working
  ]
  timeout: 30s
  retries: 3
  interval: 10s
}
```

### Notify Block
```papa
notify {
  on_success: cwb("#devops", "✅ Deploy ${version} complete in ${duration}")
  on_failure: cwb("#devops", "🔴 Deploy FAILED: ${error}")
  on_rollback: cwb("#devops", "⚠️ Rollback to ${previous_version}")
}
```

### Rollback Block
```papa
rollback {
  strategy: auto                 // auto | manual | prompt
  keep_versions: 3               // keep last 3 images
  trigger: healthcheck_fail      // or timeout, or manual
}
```

## CLI Commands

```bash
papa deploy prod                 # full deploy pipeline
papa deploy prod --dry-run       # show plan without executing
papa deploy prod --sync-only     # only sync files
papa deploy prod --build-only    # only build image
papa deploy prod --rollback      # rollback to previous version
papa deploy prod --status        # show current deployment status
papa deploy prod --history       # show deployment history
papa deploy prod --verify        # run verification only
```

## Safety Levels (inspired by DO-178C DAL)

| Level | Name | Description |
|-------|------|-------------|
| A | Critical | Dual checksum, blue-green deploy, auto-rollback, full audit |
| B | Essential | Checksum verify, rolling deploy, auto-rollback |
| C | Standard | Size verify, recreate deploy, manual rollback |
| D | Development | No verify, recreate deploy, no rollback |

```papa
ecosystem "papa-ai" {
  safety_level: B    // Essential — default for production
}
```

## Variables & Interpolation

```papa
let version = git.short_hash()
let timestamp = now().format("YYYY-MM-DD_HH:mm")
let tag = "${version}-${timestamp}"
```

## Conditional Logic

```papa
build {
  cache: if env("CI") then false else true
  requires_ram: if server.ram < 4GB then 2GB else 1GB
}
```

## Hooks

```papa
hooks {
  pre_sync:  shell("npm run lint")
  pre_build: shell("npx tsc --noEmit")
  post_build: shell("docker image prune -f")
  post_deploy: shell("npx prisma migrate deploy")
  post_verify: shell("echo 'All green!'")
}
```
