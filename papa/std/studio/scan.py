#!/usr/bin/env python3
"""
papa-lang std/studio/scan.py
Scans project and builds architecture model in SQLite
Usage: pl scan <path> [--output architecture.db]
       pl query "api passport"
       pl list api|models|pages|env
"""

import os
import re
import json
import sqlite3
import argparse
import hashlib
from pathlib import Path
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS project (
    id INTEGER PRIMARY KEY,
    name TEXT, path TEXT, scanned_at TEXT
);
CREATE TABLE IF NOT EXISTS modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    type TEXT,
    name TEXT,
    path TEXT UNIQUE,
    description TEXT,
    checksum TEXT,
    FOREIGN KEY (project_id) REFERENCES project(id)
);
CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_module TEXT, to_module TEXT, type TEXT
);
CREATE TABLE IF NOT EXISTS api_routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER, method TEXT, path TEXT, description TEXT,
    FOREIGN KEY (module_id) REFERENCES modules(id)
);
CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER, name TEXT, table_name TEXT, fields TEXT,
    FOREIGN KEY (project_id) REFERENCES project(id)
);
CREATE TABLE IF NOT EXISTS env_vars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER, name TEXT, used_in TEXT, required INTEGER DEFAULT 1
);
"""

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn

def scan_api_routes(root, conn, project_id):
    routes_found = []
    for route_file in root.glob("app/api/**/route.ts"):
        rel_path = str(route_file.relative_to(root))
        content = route_file.read_text(errors="ignore")
        methods = [m for m in ["GET","POST","PUT","DELETE","PATCH"]
                   if f"export async function {m}" in content or f"export function {m}" in content]
        api_path = "/" + str(route_file.parent.relative_to(root / "app")).replace("\\", "/")
        desc_match = re.search(r'/\*\*?\s*\n?\s*\*?\s*([^\n*]+)', content)
        description = desc_match.group(1).strip() if desc_match else ""
        checksum = hashlib.md5(content.encode()).hexdigest()[:8]
        conn.execute("INSERT OR REPLACE INTO modules (project_id, type, name, path, description, checksum) VALUES (?, 'api_route', ?, ?, ?, ?)",
                     (project_id, api_path, rel_path, description, checksum))
        module_id = conn.execute("SELECT id FROM modules WHERE path = ?", (rel_path,)).fetchone()[0]
        for method in methods:
            conn.execute("INSERT INTO api_routes (module_id, method, path, description) VALUES (?, ?, ?, ?)",
                         (module_id, method, api_path, description))
        routes_found.append((api_path, methods))
    conn.commit()
    return routes_found

def scan_pages(root, conn, project_id):
    pages_found = []
    for page_file in root.glob("app/**/page.tsx"):
        if "/api/" in str(page_file):
            continue
        rel_path = str(page_file.relative_to(root))
        content = page_file.read_text(errors="ignore")
        page_path = "/" + str(page_file.parent.relative_to(root / "app")).replace("\\", "/")
        name_match = re.search(r"export default function (\w+)", content)
        name = name_match.group(1) if name_match else page_path.split("/")[-1]
        checksum = hashlib.md5(content.encode()).hexdigest()[:8]
        conn.execute("INSERT OR REPLACE INTO modules (project_id, type, name, path, description, checksum) VALUES (?, 'page', ?, ?, ?, ?)",
                     (project_id, name, rel_path, f"Page {page_path}", checksum))
        pages_found.append(page_path)
    conn.commit()
    return pages_found

def scan_prisma(root, conn, project_id):
    models_found = []
    schema_file = root / "prisma" / "schema.prisma"
    if not schema_file.exists():
        return models_found
    content = schema_file.read_text(errors="ignore")
    for match in re.finditer(r"model (\w+)\s*\{([^}]+)\}", content, re.DOTALL):
        model_name = match.group(1)
        block = match.group(2)
        fields = []
        for line in block.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("//") and not line.startswith("@@"):
                parts = line.split()
                if len(parts) >= 2:
                    fields.append({"name": parts[0], "type": parts[1]})
        table_match = re.search(r'@@map\("([^"]+)"\)', block)
        table_name = table_match.group(1) if table_match else model_name.lower() + "s"
        conn.execute("INSERT OR REPLACE INTO models (project_id, name, table_name, fields) VALUES (?, ?, ?, ?)",
                     (project_id, model_name, table_name, json.dumps(fields)))
        models_found.append(model_name)
    conn.commit()
    return models_found

def scan_env(root, conn, project_id):
    env_usage = {}
    for ts_file in list(root.glob("app/**/*.ts")) + list(root.glob("lib/**/*.ts")):
        rel_path = str(ts_file.relative_to(root))
        content = ts_file.read_text(errors="ignore")
        for var in re.findall(r"process\.env\.([A-Z_][A-Z0-9_]+)", content):
            if var not in env_usage:
                env_usage[var] = []
            if rel_path not in env_usage[var]:
                env_usage[var].append(rel_path)
    for var_name, files in env_usage.items():
        conn.execute("INSERT OR REPLACE INTO env_vars (project_id, name, used_in) VALUES (?, ?, ?)",
                     (project_id, var_name, json.dumps(files)))
    conn.commit()
    return list(env_usage.keys())

def query_architecture(db_path, question):
    conn = sqlite3.connect(db_path)
    q = question.lower()
    results = []
    keyword = question.split()[-1]
    if any(w in q for w in ["api", "route", "endpoint"]):
        rows = conn.execute("SELECT r.method, r.path, m.path FROM api_routes r JOIN modules m ON r.module_id = m.id WHERE r.path LIKE ?",
                            (f"%{keyword}%",)).fetchall()
        if rows:
            results.append("API Routes:")
            for method, path, file in rows:
                results.append(f"  {method} {path} -> {file}")
    if any(w in q for w in ["model", "table", "db"]):
        rows = conn.execute("SELECT name, table_name FROM models WHERE LOWER(name) LIKE ?",
                            (f"%{keyword.lower()}%",)).fetchall()
        if rows:
            results.append("Models:")
            for name, table in rows:
                results.append(f"  {name} -> {table}")
    if any(w in q for w in ["page", "ui", "front"]):
        rows = conn.execute("SELECT name, path FROM modules WHERE type='page' AND LOWER(name) LIKE ?",
                            (f"%{keyword.lower()}%",)).fetchall()
        if rows:
            results.append("Pages:")
            for name, path in rows:
                results.append(f"  {name} -> {path}")
    if any(w in q for w in ["all", "stats", "summary", "list"]):
        stats = conn.execute("SELECT type, COUNT(*) FROM modules GROUP BY type").fetchall()
        results.append("Project stats:")
        for t, c in stats:
            results.append(f"  {t}: {c}")
        results.append(f"  models: {conn.execute('SELECT COUNT(*) FROM models').fetchone()[0]}")
    conn.close()
    return "\n".join(results) if results else f"Not found: {question}"

def cmd_scan(args):
    root = Path(args.path).resolve()
    db_path = args.output or str(root / "architecture.db")
    print(f"Scanning: {root}")
    conn = init_db(db_path)
    try:
        pkg = json.loads((root / "package.json").read_text())
        project_name = pkg.get("name", root.name)
    except:
        project_name = root.name
    conn.execute("DELETE FROM project")
    conn.execute("INSERT INTO project (name, path, scanned_at) VALUES (?, ?, ?)",
                 (project_name, str(root), datetime.now().isoformat()))
    project_id = conn.execute("SELECT id FROM project").fetchone()[0]
    for table in ["modules", "edges", "api_routes", "models", "env_vars"]:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    routes = scan_api_routes(root, conn, project_id)
    print(f"  API routes: {len(routes)}")
    pages = scan_pages(root, conn, project_id)
    print(f"  Pages: {len(pages)}")
    models = scan_prisma(root, conn, project_id)
    print(f"  Prisma models: {len(models)}")
    env_vars = scan_env(root, conn, project_id)
    print(f"  ENV vars: {len(env_vars)}")
    print(f"\nDone! Architecture saved: {db_path}")
    print(f"Query: python3 scan.py query 'api passport'")
    conn.close()

def cmd_query(args):
    db_path = args.db or "architecture.db"
    if not os.path.exists(db_path):
        print(f"DB not found: {db_path}. Run: pl scan <path>")
        return
    print(query_architecture(db_path, args.question))

def cmd_list(args):
    db_path = args.db or "architecture.db"
    conn = sqlite3.connect(db_path)
    if args.type == "api":
        for method, path, file in conn.execute("SELECT r.method, r.path, m.path FROM api_routes r JOIN modules m ON r.module_id=m.id ORDER BY r.path").fetchall():
            print(f"  {method:6} {path:40} -> {file}")
    elif args.type == "models":
        for name, table in conn.execute("SELECT name, table_name FROM models ORDER BY name").fetchall():
            print(f"  {name:30} -> {table}")
    elif args.type == "pages":
        for name, path in conn.execute("SELECT name, path FROM modules WHERE type='page' ORDER BY path").fetchall():
            print(f"  {name:30} -> {path}")
    elif args.type == "env":
        for name, used_in in conn.execute("SELECT name, used_in FROM env_vars ORDER BY name").fetchall():
            print(f"  {name:35} ({len(json.loads(used_in))} files)")
    conn.close()

def main():
    parser = argparse.ArgumentParser(prog="pl scan", description="papa-lang Architecture Scanner")
    sub = parser.add_subparsers(dest="command")
    s = sub.add_parser("scan"); s.add_argument("path"); s.add_argument("--output", "-o")
    q = sub.add_parser("query"); q.add_argument("question"); q.add_argument("--db")
    l = sub.add_parser("list"); l.add_argument("type", choices=["api","models","pages","env"]); l.add_argument("--db")
    args = parser.parse_args()
    if args.command == "scan": cmd_scan(args)
    elif args.command == "query": cmd_query(args)
    elif args.command == "list": cmd_list(args)
    else: parser.print_help()

if __name__ == "__main__":
    main()
