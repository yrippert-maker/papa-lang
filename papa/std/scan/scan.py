#!/usr/bin/env python3
"""
pl scan + pl collect — Zero-Hallucination project scanner
Papa-Lang Standard Library: scan module

Scans project directories, builds dependency graphs,
and collects files for AI analysis with zero hallucination guarantees.

Usage:
    pl scan /path/to/project --output architecture.db
    pl scan /path/to/project --format json
    pl collect --db architecture.db --query "auth files" --max 20
"""

import os
import sys
import re
import json
import sqlite3
import hashlib
import argparse
from pathlib import Path
from typing import Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict

__version__ = "0.2.0"
__author__ = "papa-nexus"

# ─────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────

@dataclass
class FileNode:
    """Represents a single file in the project."""
    path: str
    relative_path: str
    extension: str
    size: int
    lines: int
    hash: str
    language: str
    module: str
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    scanned_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class Edge:
    """Represents a dependency edge between two files."""
    source: str
    target: str
    edge_type: str  # import, re-export, type-import, dynamic-import
    weight: float = 1.0


@dataclass
class ScanResult:
    """Complete scan result for a project."""
    project_root: str
    total_files: int
    total_lines: int
    nodes: list[FileNode] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    languages: dict[str, int] = field(default_factory=dict)
    scanned_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ─────────────────────────────────────────────
# Language Detection
# ─────────────────────────────────────────────

LANGUAGE_MAP = {
    '.ts': 'typescript', '.tsx': 'typescript',
    '.js': 'javascript', '.jsx': 'javascript',
    '.mjs': 'javascript', '.cjs': 'javascript',
    '.py': 'python', '.pyx': 'python',
    '.rs': 'rust', '.go': 'go',
    '.prisma': 'prisma', '.sql': 'sql',
    '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml',
    '.toml': 'toml', '.md': 'markdown',
    '.sh': 'shell', '.bash': 'shell',
    '.css': 'css', '.scss': 'scss',
    '.html': 'html', '.vue': 'vue',
    '.svelte': 'svelte', '.astro': 'astro',
}

IGNORE_DIRS = {
    'node_modules', '.git', '.next', '__pycache__', 'dist',
    'build', '.turbo', 'coverage', '.cache', 'target',
    '.venv', 'venv', 'env', '.egg-info',
}

IGNORE_EXTENSIONS = {
    '.lock', '.map', '.min.js', '.min.css',
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
    '.woff', '.woff2', '.ttf', '.eot',
    '.zip', '.tar', '.gz', '.br',
}


def detect_language(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    return LANGUAGE_MAP.get(ext, 'unknown')


# ─────────────────────────────────────────────
# Parsers
# ─────────────────────────────────────────────

class TypeScriptParser:
    """Extract imports, exports, functions, classes from TS/JS files."""

    IMPORT_RE = re.compile(
        r"(?:import\s+(?:{[^}]+}|\w+|\*\s+as\s+\w+)\s+from\s+['\"]([\./@\w-]+)['\"]]"
        r"|require\(['\"]([\./@\w-]+)['\"]]\))",
        re.MULTILINE,
    )
    EXPORT_RE = re.compile(
        r"export\s+(?:default\s+)?(?:function|class|const|let|var|type|interface|enum)\s+(\w+)",
        re.MULTILINE,
    )
    FUNCTION_RE = re.compile(
        r"(?:export\s+)?(?:async\s+)?function\s+(\w+)|(?:const|let)\s+(\w+)\s*=\s*(?:async\s+)?\(",
        re.MULTILINE,
    )
    CLASS_RE = re.compile(r"(?:export\s+)?class\s+(\w+)", re.MULTILINE)

    @staticmethod
    def parse(content: str, filepath: str) -> dict:
        imports = []
        for m in re.finditer(r"(?:import|from)\s+['\"]([\./@\w-]+)['\"]]", content):
            imports.append(m.group(1))
        for m in re.finditer(r"require\(['\"]([\./@\w-]+)['\"]]\)", content):
            imports.append(m.group(1))

        exports = [m.group(1) for m in re.finditer(
            r"export\s+(?:default\s+)?(?:function|class|const|let|var|type|interface|enum)\s+(\w+)", content
        )]
        functions = []
        for m in re.finditer(r"(?:async\s+)?function\s+(\w+)", content):
            functions.append(m.group(1))
        for m in re.finditer(r"(?:const|let)\s+(\w+)\s*=\s*(?:async\s+)?\(", content):
            functions.append(m.group(1))

        classes = [m.group(1) for m in re.finditer(r"class\s+(\w+)", content)]

        return {
            'imports': imports,
            'exports': exports,
            'functions': functions,
            'classes': classes,
        }


class PythonParser:
    """Extract imports, functions, classes from Python files."""

    @staticmethod
    def parse(content: str, filepath: str) -> dict:
        imports = []
        for m in re.finditer(r"^(?:from\s+(\S+)\s+import|import\s+(\S+))", content, re.MULTILINE):
            imports.append(m.group(1) or m.group(2))

        functions = [m.group(1) for m in re.finditer(
            r"^(?:async\s+)?def\s+(\w+)", content, re.MULTILINE
        )]
        classes = [m.group(1) for m in re.finditer(
            r"^class\s+(\w+)", content, re.MULTILINE
        )]

        return {
            'imports': imports,
            'exports': functions + classes,
            'functions': functions,
            'classes': classes,
        }


class PrismaParser:
    """Extract models and enums from Prisma schema files."""

    @staticmethod
    def parse(content: str, filepath: str) -> dict:
        models = [m.group(1) for m in re.finditer(r"^model\s+(\w+)", content, re.MULTILINE)]
        enums = [m.group(1) for m in re.finditer(r"^enum\s+(\w+)", content, re.MULTILINE)]
        return {
            'imports': [],
            'exports': models + enums,
            'functions': [],
            'classes': models,
        }


PARSERS = {
    'typescript': TypeScriptParser,
    'javascript': TypeScriptParser,
    'python': PythonParser,
    'prisma': PrismaParser,
}


# ─────────────────────────────────────────────
# Scanner
# ─────────────────────────────────────────────

class ProjectScanner:
    """Scans a project directory and builds a dependency graph."""

    def __init__(self, root: str, max_file_size: int = 512_000):
        self.root = Path(root).resolve()
        self.max_file_size = max_file_size
        self.nodes: list[FileNode] = []
        self.edges: list[Edge] = []
        self.languages: dict[str, int] = {}

    def should_ignore(self, path: Path) -> bool:
        parts = path.relative_to(self.root).parts
        for part in parts:
            if part in IGNORE_DIRS:
                return True
        if path.suffix in IGNORE_EXTENSIONS:
            return True
        if path.name.startswith('.'):
            return True
        return False

    def compute_hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()[:16]

    def infer_module(self, rel_path: str) -> str:
        parts = Path(rel_path).parts
        if len(parts) >= 2:
            return parts[0] + '/' + parts[1]
        return parts[0] if parts else 'root'

    def scan_file(self, filepath: Path) -> Optional[FileNode]:
        if self.should_ignore(filepath):
            return None
        if filepath.stat().st_size > self.max_file_size:
            return None

        try:
            content_bytes = filepath.read_bytes()
            content = content_bytes.decode('utf-8', errors='replace')
        except (OSError, PermissionError):
            return None

        rel_path = str(filepath.relative_to(self.root))
        language = detect_language(str(filepath))
        lines = content.count('\n') + 1

        parser = PARSERS.get(language)
        parsed = parser.parse(content, str(filepath)) if parser else {
            'imports': [], 'exports': [], 'functions': [], 'classes': []
        }

        node = FileNode(
            path=str(filepath),
            relative_path=rel_path,
            extension=filepath.suffix,
            size=len(content_bytes),
            lines=lines,
            hash=self.compute_hash(content_bytes),
            language=language,
            module=self.infer_module(rel_path),
            imports=parsed['imports'],
            exports=parsed['exports'],
            functions=parsed['functions'],
            classes=parsed['classes'],
        )

        self.languages[language] = self.languages.get(language, 0) + 1
        return node

    def resolve_import(self, source_path: str, import_path: str) -> Optional[str]:
        if not import_path.startswith('.'):
            return None  # external package
        source_dir = Path(source_path).parent
        resolved = (source_dir / import_path).resolve()
        for ext in ['.ts', '.tsx', '.js', '.jsx', '/index.ts', '/index.tsx', '/index.js']:
            candidate = Path(str(resolved) + ext)
            if candidate.exists():
                try:
                    return str(candidate.relative_to(self.root))
                except ValueError:
                    return None
        return None

    def build_edges(self):
        path_map = {n.relative_path: n for n in self.nodes}
        for node in self.nodes:
            for imp in node.imports:
                target = self.resolve_import(node.relative_path, imp)
                if target and target in path_map:
                    self.edges.append(Edge(
                        source=node.relative_path,
                        target=target,
                        edge_type='import',
                    ))

    def scan(self) -> ScanResult:
        for filepath in self.root.rglob('*'):
            if filepath.is_file():
                node = self.scan_file(filepath)
                if node:
                    self.nodes.append(node)

        self.build_edges()

        return ScanResult(
            project_root=str(self.root),
            total_files=len(self.nodes),
            total_lines=sum(n.lines for n in self.nodes),
            nodes=self.nodes,
            edges=self.edges,
            languages=self.languages,
        )


# ─────────────────────────────────────────────
# Database Storage
# ─────────────────────────────────────────────

class ArchitectureDB:
    """SQLite storage for scan results — architecture.db."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                path TEXT PRIMARY KEY,
                relative_path TEXT,
                extension TEXT,
                size INTEGER,
                lines INTEGER,
                hash TEXT,
                language TEXT,
                module TEXT,
                imports TEXT,
                exports TEXT,
                functions TEXT,
                classes TEXT,
                scanned_at TEXT
            );
            CREATE TABLE IF NOT EXISTS edges (
                source TEXT,
                target TEXT,
                edge_type TEXT,
                weight REAL DEFAULT 1.0,
                PRIMARY KEY (source, target, edge_type)
            );
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_nodes_module ON nodes(module);
            CREATE INDEX IF NOT EXISTS idx_nodes_language ON nodes(language);
            CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target);
        """)
        self.conn.commit()

    def store(self, result: ScanResult):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM nodes")
        cur.execute("DELETE FROM edges")

        for node in result.nodes:
            cur.execute(
                """INSERT OR REPLACE INTO nodes 
                (path, relative_path, extension, size, lines, hash, 
                 language, module, imports, exports, functions, classes, scanned_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    node.relative_path, node.relative_path, node.extension,
                    node.size, node.lines, node.hash, node.language,
                    node.module, json.dumps(node.imports), json.dumps(node.exports),
                    json.dumps(node.functions), json.dumps(node.classes), node.scanned_at,
                ),
            )

        for edge in result.edges:
            cur.execute(
                "INSERT OR REPLACE INTO edges (source, target, edge_type, weight) VALUES (?, ?, ?, ?)",
                (edge.source, edge.target, edge.edge_type, edge.weight),
            )

        cur.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            ('last_scan', result.scanned_at),
        )
        cur.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            ('total_files', str(result.total_files)),
        )
        cur.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            ('total_lines', str(result.total_lines)),
        )
        cur.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            ('languages', json.dumps(result.languages)),
        )

        self.conn.commit()

    def query_files(self, query: str, max_results: int = 20) -> list[dict]:
        cur = self.conn.cursor()
        terms = query.lower().split()
        conditions = []
        params = []
        for term in terms:
            conditions.append(
                "(LOWER(relative_path) LIKE ? OR LOWER(module) LIKE ? OR LOWER(functions) LIKE ? OR LOWER(classes) LIKE ?)"
            )
            like = f"%{term}%"
            params.extend([like, like, like, like])

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM nodes WHERE {where} ORDER BY lines DESC LIMIT ?"
        params.append(max_results)

        cur.execute(sql, params)
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def get_dependencies(self, file_path: str) -> list[dict]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM edges WHERE source = ? OR target = ?",
            (file_path, file_path),
        )
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def close(self):
        self.conn.close()


# ─────────────────────────────────────────────
# Collector (pl collect)
# ─────────────────────────────────────────────

class FileCollector:
    """Collects file contents for AI context based on architecture.db queries."""

    def __init__(self, db_path: str, project_root: str = '.'):
        self.db = ArchitectureDB(db_path)
        self.project_root = Path(project_root).resolve()

    def collect(self, query: str, max_files: int = 20) -> list[dict]:
        files = self.db.query_files(query, max_files)
        result = []
        for f in files:
            filepath = self.project_root / f['relative_path']
            try:
                content = filepath.read_text(encoding='utf-8', errors='replace')
                result.append({
                    'path': f['relative_path'],
                    'language': f['language'],
                    'lines': f['lines'],
                    'module': f['module'],
                    'content': content,
                })
            except (OSError, FileNotFoundError):
                result.append({
                    'path': f['relative_path'],
                    'language': f['language'],
                    'lines': f['lines'],
                    'module': f['module'],
                    'content': f'[FILE NOT FOUND: {f["relative_path"]}]',
                })
        return result

    def collect_module(self, module: str) -> list[dict]:
        return self.collect(module)

    def close(self):
        self.db.close()


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def cmd_scan(args):
    print(f"Scanning: {args.path}")
    scanner = ProjectScanner(args.path)
    result = scanner.scan()

    if args.format == 'json':
        output = json.dumps({
            'project_root': result.project_root,
            'total_files': result.total_files,
            'total_lines': result.total_lines,
            'languages': result.languages,
            'nodes': [asdict(n) for n in result.nodes],
            'edges': [asdict(e) for e in result.edges],
        }, indent=2)
        if args.output:
            Path(args.output).write_text(output)
        else:
            print(output)
    else:
        db_path = args.output or 'architecture.db'
        db = ArchitectureDB(db_path)
        db.store(result)
        db.close()
        print(f"Stored {result.total_files} files, {len(result.edges)} edges -> {db_path}")

    print(f"Total: {result.total_files} files, {result.total_lines} lines")
    for lang, count in sorted(result.languages.items(), key=lambda x: -x[1])[:10]:
        print(f"  {lang}: {count} files")


def cmd_collect(args):
    collector = FileCollector(args.db, args.root or '.')
    files = collector.collect(args.query, args.max)

    if args.format == 'json':
        print(json.dumps(files, indent=2))
    else:
        for f in files:
            print(f"\n{'='*60}")
            print(f"FILE: {f['path']} ({f['language']}, {f['lines']} lines)")
            print(f"{'='*60}")
            print(f['content'])

    collector.close()


def main():
    parser = argparse.ArgumentParser(
        prog='pl',
        description='Papa-Lang Project Scanner — Zero-Hallucination tools',
    )
    subparsers = parser.add_subparsers(dest='command')

    # pl scan
    scan_parser = subparsers.add_parser('scan', help='Scan project directory')
    scan_parser.add_argument('path', help='Project root path')
    scan_parser.add_argument('--output', '-o', help='Output file path')
    scan_parser.add_argument('--format', '-f', choices=['db', 'json'], default='db')

    # pl collect
    collect_parser = subparsers.add_parser('collect', help='Collect files for AI context')
    collect_parser.add_argument('--db', required=True, help='Path to architecture.db')
    collect_parser.add_argument('--query', '-q', required=True, help='Search query')
    collect_parser.add_argument('--max', type=int, default=20, help='Max files to collect')
    collect_parser.add_argument('--root', help='Project root for reading files')
    collect_parser.add_argument('--format', '-f', choices=['text', 'json'], default='text')

    args = parser.parse_args()

    if args.command == 'scan':
        cmd_scan(args)
    elif args.command == 'collect':
        cmd_collect(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
