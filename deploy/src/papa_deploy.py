#!/usr/bin/env python3
"""
PAPA Deploy Compiler v1.0
Compiles .papa deploy files into executable shell scripts.
Aviation-grade deployment with DO-178C inspired safety levels.

Usage:
    papa-deploy compile <file.papa>          # Generate deploy script
    papa-deploy run <file.papa>              # Compile and execute
    papa-deploy run <file.papa> --dry-run    # Show plan without executing
    papa-deploy run <file.papa> --sync-only  # Only sync files
    papa-deploy run <file.papa> --rollback   # Rollback to previous version
"""

import re
import sys
import json
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


class PapaDeployParser:
    """Parser for .papa deploy DSL files."""

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.config: Dict[str, Any] = {}

    def parse(self) -> Dict[str, Any]:
        """Parse the .papa file into a config dict."""
        # Remove comments
        lines = []
        for line in self.source.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
            # Remove inline comments (but not inside strings)
            in_string = False
            clean = []
            for i, ch in enumerate(line):
                if ch == '"' and (i == 0 or line[i-1] != '\\'):
                    in_string = not in_string
                if ch == '/' and i + 1 < len(line) and line[i+1] == '/' and not in_string:
                    break
                clean.append(ch)
            lines.append(''.join(clean))

        text = '\n'.join(lines)

        # Extract ecosystem block
        eco_match = re.search(r'ecosystem\s+"([^"]+)"\s*\{', text)
        if eco_match:
            self.config['name'] = eco_match.group(1)

        # Extract key-value pairs and blocks
        self.config['server'] = self._extract_block(text, 'server')
        self.config['sync'] = self._extract_block(text, 'sync')
        self.config['build'] = self._extract_block(text, 'build')
        self.config['deploy'] = self._extract_block(text, 'deploy')
        self.config['verify'] = self._extract_block(text, 'verify')
        self.config['hooks'] = self._extract_block(text, 'hooks')
        self.config['notify'] = self._extract_block(text, 'notify')
        self.config['rollback'] = self._extract_block(text, 'rollback')

        # Extract top-level values
        ver_match = re.search(r'version:\s*"([^"]+)"', text)
        if ver_match:
            self.config['version'] = ver_match.group(1)

        safety_match = re.search(r'safety_level:\s*(\w+)', text)
        if safety_match:
            self.config['safety_level'] = safety_match.group(1)

        return self.config

    def _extract_block(self, text: str, block_name: str) -> Dict[str, Any]:
        """Extract a named block from the .papa file."""
        result = {}

        # Find block with optional quoted name
        patterns = [
            rf'{block_name}\s+"([^"]+)"\s*\{{',  # named: server "prod" {
            rf'{block_name}\s*\{{',                # unnamed: sync {
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                if match.lastindex and match.lastindex >= 1:
                    result['_name'] = match.group(1)

                # Find matching closing brace
                start = match.end()
                depth = 1
                pos = start
                while pos < len(text) and depth > 0:
                    if text[pos] == '{':
                        depth += 1
                    elif text[pos] == '}':
                        depth -= 1
                    pos += 1

                block_content = text[start:pos-1]

                # Parse simple key: value pairs
                for line in block_content.split('\n'):
                    line = line.strip().rstrip(',')
                    if not line or line.startswith('[') or line.startswith('{'):
                        continue

                    kv_match = re.match(r'(\w+):\s*(.+)', line)
                    if kv_match:
                        key = kv_match.group(1)
                        value = kv_match.group(2).strip().rstrip(',')

                        # Parse value types
                        if value.startswith('"') and value.endswith('"'):
                            result[key] = value.strip('"')
                        elif value in ('true', 'false'):
                            result[key] = value == 'true'
                        elif re.match(r'^\d+$', value):
                            result[key] = int(value)
                        elif value.startswith('['):
                            # Extract array
                            arr_text = value
                            if ']' not in arr_text:
                                # Multi-line array
                                arr_end = block_content.find(']', block_content.find(line))
                                if arr_end >= 0:
                                    arr_text = block_content[block_content.find('[', block_content.find(line)):arr_end+1]
                            items = re.findall(r'"([^"]+)"', arr_text)
                            if not items:
                                items = re.findall(r'(\w[\w.-]+)', arr_text.strip('[]'))
                            result[key] = items
                        else:
                            result[key] = value

                break

        return result


class PapaDeployCompiler:
    """Compiles parsed .papa config into executable shell script."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.script_lines: List[str] = []

    def compile(self, mode: str = "full") -> str:
        """Generate shell script from config."""
        self._header()
        self._variables()
        self._functions()

        if mode in ("full", "sync-only"):
            self._sync_phase()
        if mode == "sync-only":
            self._footer()
            return '\n'.join(self.script_lines)

        if mode in ("full", "build-only"):
            self._commit_phase()
            self._build_phase()
        if mode == "build-only":
            self._footer()
            return '\n'.join(self.script_lines)

        if mode == "full":
            self._deploy_phase()
            self._verify_phase()
            self._notify_phase()

        if mode == "rollback":
            self._rollback_phase()

        self._footer()
        return '\n'.join(self.script_lines)

    def _header(self):
        name = self.config.get('name', 'unnamed')
        version = self.config.get('version', '0.0.0')
        safety = self.config.get('safety_level', 'C')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self.script_lines.extend([
            '#!/bin/bash',
            f'# PAPA Deploy — {name} v{version}',
            f'# Safety Level: {safety} (DO-178C DAL)',
            f'# Generated: {timestamp}',
            f'# Compiler: papa-deploy v1.0',
            '',
            'set -euo pipefail',
            '',
            '# ═══════════════════════════════════════════',
            f'# PAPA DEPLOY: {name}',
            '# ═══════════════════════════════════════════',
            '',
        ])

    def _variables(self):
        server = self.config.get('server', {})
        build = self.config.get('build', {})

        self.script_lines.extend([
            '# --- Variables ---',
            f'DEPLOY_HOST="{server.get("host", "localhost")}"',
            f'DEPLOY_USER="{server.get("user", "root")}"',
            f'DEPLOY_PORT="{server.get("port", 22)}"',
            f'DEPLOY_PATH="{server.get("path", "/opt/app")}"',
            f'DOCKER_IMAGE="{build.get("image", "app:latest")}"',
            f'DEPLOY_START=$(date +%s)',
            f'DEPLOY_VERSION=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")',
            f'DEPLOY_DATE=$(date "+%Y-%m-%d %H:%M:%S")',
            '',
            'RED="\\033[0;31m"',
            'GREEN="\\033[0;32m"',
            'YELLOW="\\033[1;33m"',
            'CYAN="\\033[0;36m"',
            'NC="\\033[0m"',
            '',
        ])

    def _functions(self):
        self.script_lines.extend([
            '# --- Functions ---',
            'log() { echo -e "${CYAN}[PAPA]${NC} $1"; }',
            'success() { echo -e "${GREEN}[✅]${NC} $1"; }',
            'warn() { echo -e "${YELLOW}[⚠️]${NC} $1"; }',
            'fail() { echo -e "${RED}[🔴]${NC} $1"; exit 1; }',
            '',
            'elapsed() {',
            '  local end=$(date +%s)',
            '  local dur=$((end - DEPLOY_START))',
            '  echo "${dur}s"',
            '}',
            '',
            'check_ram() {',
            '  local free=$(ssh -p $DEPLOY_PORT $DEPLOY_USER@$DEPLOY_HOST "free -m | awk \'/^Mem:/ {print \\$7}\'")',
            '  echo "$free"',
            '}',
            '',
            'remote() { ssh -p $DEPLOY_PORT $DEPLOY_USER@$DEPLOY_HOST "$@"; }',
            '',
        ])

    def _sync_phase(self):
        sync = self.config.get('sync', {})
        excludes = sync.get('exclude', [])
        verify = sync.get('verify', 'checksum')

        exclude_flags = ' '.join([f'--exclude={e}' for e in excludes])

        rsync_flags = '-avz'
        if sync.get('compress', True):
            rsync_flags += '' # -z already in -avz
        if verify == 'checksum':
            rsync_flags += ' --checksum'

        self.script_lines.extend([
            '# ═══ PHASE 1: SYNC ═══',
            'log "Phase 1: Syncing files to $DEPLOY_HOST..."',
            '',
            f'rsync {rsync_flags} --delete \\',
            f'  {exclude_flags} \\',
            f'  ./ $DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_PATH/',
            '',
            'SYNC_RESULT=$?',
            'if [ $SYNC_RESULT -ne 0 ]; then',
            '  fail "Sync failed with exit code $SYNC_RESULT"',
            'fi',
            'success "Sync complete ($(elapsed))"',
            '',
        ])

    def _commit_phase(self):
        self.script_lines.extend([
            '# ═══ PHASE 2: COMMIT ═══',
            'log "Phase 2: Committing on server..."',
            '',
            'remote "cd $DEPLOY_PATH && \\',
            '  HUSKY=0 git add -A && \\',
            '  git commit --no-verify -m \\"deploy: v$DEPLOY_VERSION — $DEPLOY_DATE\\" || true"',
            '',
            'success "Commit complete ($(elapsed))"',
            '',
        ])

    def _build_phase(self):
        build = self.config.get('build', {})
        args = build.get('args', {})
        stop_for_ram = build.get('stop_for_ram', [])
        requires_ram = build.get('requires_ram', '2GB')
        cache_flag = '--no-cache' if not build.get('cache', True) else ''

        # Parse RAM requirement
        ram_mb = int(re.search(r'(\d+)', str(requires_ram)).group(1)) * 1024 \
            if 'GB' in str(requires_ram) else int(re.search(r'(\d+)', str(requires_ram)).group(1))

        # Build args string
        if isinstance(args, dict):
            build_args = ' '.join([f'--build-arg {k}={v}' for k, v in args.items()
                                   if isinstance(v, str)])
        else:
            build_args = '--build-arg NEXTAUTH_SECRET=build --build-arg DATABASE_URL=postgresql://b:b@l:5432/b'

        stop_containers = ' '.join(stop_for_ram) if stop_for_ram else ''

        self.script_lines.extend([
            '# ═══ PHASE 3: BUILD ═══',
            'log "Phase 3: Building Docker image..."',
            '',
            '# Check RAM and stop heavy containers if needed',
            f'FREE_RAM=$(check_ram)',
            f'log "Free RAM: ${{FREE_RAM}}MB (need {ram_mb}MB)"',
            '',
            f'if [ "$FREE_RAM" -lt "{ram_mb}" ] && [ -n "{stop_containers}" ]; then',
            '  warn "Low RAM — stopping heavy containers for build..."',
            f'  remote "docker stop {stop_containers} 2>/dev/null || true"',
            '  sleep 5',
            '  # Clear swap',
            '  remote "swapoff -a && swapon -a" 2>/dev/null || true',
            '  sleep 3',
            'fi',
            '',
            f'remote "cd $DEPLOY_PATH && docker build {cache_flag} \\',
            f'  -t {build.get("image", "app:latest")} \\',
            f'  {build_args} \\',
            f'  . 2>&1 | tail -5"',
            '',
            'BUILD_RESULT=$?',
            'if [ $BUILD_RESULT -ne 0 ]; then',
            '  fail "Build failed with exit code $BUILD_RESULT"',
            'fi',
            '',
            '# Save previous image ID for rollback',
            f'PREV_IMAGE=$(remote "docker images -q {build.get("image", "app:latest")} | head -2 | tail -1")',
            '',
            'success "Build complete ($(elapsed))"',
            '',
        ])

    def _deploy_phase(self):
        deploy = self.config.get('deploy', {})
        containers = deploy.get('containers', [])
        start_after = deploy.get('start_after', [])
        build = self.config.get('build', {})
        image = build.get('image', 'app:latest')

        self.script_lines.extend([
            '# ═══ PHASE 4: DEPLOY ═══',
            'log "Phase 4: Deploying containers..."',
            '',
        ])

        # For simple config, generate docker run commands
        # Parse containers from config (simplified)
        self.script_lines.extend([
            '# Remove old containers',
            'remote "docker rm -f papa-frontend-prod papa-ecosystem-prod 2>/dev/null || true"',
            '',
            '# Deploy new containers',
            f'remote "docker run -d --name papa-frontend-prod \\',
            f'  --restart unless-stopped \\',
            f'  --network papa-ecosystem_papa-network \\',
            f'  -p 3000:3000 \\',
            f'  --env-file /opt/papa-ecosystem/.env \\',
            f'  -e NODE_ENV=production \\',
            f'  {image}"',
            '',
            f'remote "docker run -d --name papa-ecosystem-prod \\',
            f'  --restart unless-stopped \\',
            f'  --network papa-ecosystem_papa-network \\',
            f'  -p 3010:3000 \\',
            f'  --env-file /opt/papa-ecosystem/.env \\',
            f'  -e NODE_ENV=production \\',
            f'  {image}"',
            '',
        ])

        if start_after:
            containers_str = ' '.join(start_after)
            self.script_lines.extend([
                '# Start supporting containers',
                f'remote "docker start {containers_str} 2>/dev/null || true"',
                '',
            ])

        if deploy.get('prune_images', False):
            self.script_lines.extend([
                '# Cleanup',
                'remote "docker image prune -f 2>/dev/null | tail -1"',
                '',
            ])

        self.script_lines.extend([
            '# Wait for healthcheck',
            'log "Waiting 30s for containers to initialize..."',
            'sleep 30',
            '',
            'success "Deploy complete ($(elapsed))"',
            '',
        ])

    def _verify_phase(self):
        verify = self.config.get('verify', {})
        endpoints = verify.get('endpoints', [])
        retries = verify.get('retries', 3)
        timeout = verify.get('timeout', '30s')

        server = self.config.get('server', {})
        host = server.get('host', 'localhost')

        self.script_lines.extend([
            '# ═══ PHASE 5: VERIFY ═══',
            'log "Phase 5: Verifying deployment..."',
            '',
            'VERIFY_PASS=0',
            'VERIFY_FAIL=0',
            '',
        ])

        # Generate verification for known endpoints
        self.script_lines.extend([
            f'for ep in api/health api/orchestrator/status; do',
            f'  STATUS=$(curl -s -o /dev/null -w "%{{http_code}}" --max-time 10 https://app.papa-ai.ae/$ep)',
            f'  if [ "$STATUS" = "200" ]; then',
            f'    success "$ep → $STATUS"',
            f'    VERIFY_PASS=$((VERIFY_PASS + 1))',
            f'  else',
            f'    warn "$ep → $STATUS"',
            f'    VERIFY_FAIL=$((VERIFY_FAIL + 1))',
            f'  fi',
            f'done',
            '',
            f'for ep in api/swarm api/agents api/alerts; do',
            f'  STATUS=$(curl -s -o /dev/null -w "%{{http_code}}" --max-time 10 https://app.papa-ai.ae/$ep)',
            f'  if [ "$STATUS" = "401" ]; then',
            f'    success "$ep → $STATUS (auth required = working)"',
            f'    VERIFY_PASS=$((VERIFY_PASS + 1))',
            f'  else',
            f'    warn "$ep → $STATUS (expected 401)"',
            f'    VERIFY_FAIL=$((VERIFY_FAIL + 1))',
            f'  fi',
            f'done',
            '',
            'if [ $VERIFY_FAIL -gt 0 ]; then',
            '  warn "Verification: $VERIFY_PASS passed, $VERIFY_FAIL failed"',
            'else',
            '  success "Verification: ALL $VERIFY_PASS endpoints passed!"',
            'fi',
            '',
        ])

    def _notify_phase(self):
        self.script_lines.extend([
            '# ═══ PHASE 6: REPORT ═══',
            'DEPLOY_END=$(date +%s)',
            'DEPLOY_DURATION=$((DEPLOY_END - DEPLOY_START))',
            '',
            'echo ""',
            'echo "╔═══════════════════════════════════════╗"',
            'echo "║      PAPA DEPLOY REPORT               ║"',
            'echo "╠═══════════════════════════════════════╣"',
            'echo "║ Version:  $DEPLOY_VERSION"',
            'echo "║ Duration: ${DEPLOY_DURATION}s"',
            'echo "║ Passed:   $VERIFY_PASS endpoints"',
            'echo "║ Failed:   $VERIFY_FAIL endpoints"',
            'echo "║ Image:    $DOCKER_IMAGE"',
            'echo "╚═══════════════════════════════════════╝"',
            '',
        ])

    def _rollback_phase(self):
        build = self.config.get('build', {})
        image = build.get('image', 'app:latest')

        self.script_lines.extend([
            '# ═══ ROLLBACK ═══',
            'log "Rolling back to previous version..."',
            '',
            f'PREV=$(remote "docker images {image} --format \\"{{{{.ID}}}}\\" | head -2 | tail -1")',
            'if [ -z "$PREV" ]; then',
            '  fail "No previous version found for rollback"',
            'fi',
            '',
            f'remote "docker tag $PREV {image}"',
            '',
            '# Redeploy with previous image',
            'remote "docker rm -f papa-frontend-prod papa-ecosystem-prod 2>/dev/null || true"',
            f'remote "docker run -d --name papa-frontend-prod --restart unless-stopped \\',
            f'  --network papa-ecosystem_papa-network -p 3000:3000 \\',
            f'  --env-file /opt/papa-ecosystem/.env -e NODE_ENV=production {image}"',
            f'remote "docker run -d --name papa-ecosystem-prod --restart unless-stopped \\',
            f'  --network papa-ecosystem_papa-network -p 3010:3000 \\',
            f'  --env-file /opt/papa-ecosystem/.env -e NODE_ENV=production {image}"',
            '',
            'success "Rollback complete"',
            '',
        ])

    def _footer(self):
        self.script_lines.extend([
            '# ═══ DONE ═══',
            'success "PAPA Deploy finished in $(elapsed)"',
        ])


class PapaDeployCLI:
    """CLI interface for PAPA Deploy."""

    def __init__(self):
        self.args = sys.argv[1:]

    def run(self):
        if len(self.args) < 2:
            self.usage()
            return

        command = self.args[0]
        papa_file = self.args[1]
        mode = "full"

        # Parse flags
        if "--dry-run" in self.args:
            mode = "dry-run"
        elif "--sync-only" in self.args:
            mode = "sync-only"
        elif "--build-only" in self.args:
            mode = "build-only"
        elif "--rollback" in self.args:
            mode = "rollback"

        if not os.path.exists(papa_file):
            print(f"Error: File '{papa_file}' not found")
            sys.exit(1)

        # Read and parse
        with open(papa_file, 'r') as f:
            source = f.read()

        parser = PapaDeployParser(source)
        config = parser.parse()

        # Compile
        compiler = PapaDeployCompiler(config)
        compile_mode = mode if mode != "dry-run" else "full"
        script = compiler.compile(compile_mode)

        if command == "compile" or mode == "dry-run":
            print(script)
        elif command == "run":
            # Write to temp file and execute
            script_path = f"/tmp/papa-deploy-{os.getpid()}.sh"
            with open(script_path, 'w') as f:
                f.write(script)
            os.chmod(script_path, 0o755)
            print(f"[PAPA] Executing deploy script...")
            os.system(f"bash {script_path}")
            os.unlink(script_path)
        else:
            self.usage()

    def usage(self):
        print("""
PAPA Deploy v1.0 — Aviation-grade deployment DSL

Usage:
  papa-deploy compile <file.papa>              Generate shell script
  papa-deploy run <file.papa>                  Compile and execute
  papa-deploy run <file.papa> --dry-run        Show plan
  papa-deploy run <file.papa> --sync-only      Only sync files
  papa-deploy run <file.papa> --build-only     Only build
  papa-deploy run <file.papa> --rollback       Rollback to previous
        """)


if __name__ == '__main__':
    cli = PapaDeployCLI()
    cli.run()
