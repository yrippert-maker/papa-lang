"""
PAPA Lang — Self-Evolving CLI (lib/cli_evolve.py)
==================================================

Команды:
  papa evolve analyze   — анализ кодовой базы
  papa evolve suggest   — предложения улучшений
  papa evolve run       — полный цикл (analyze → suggest → create → test → commit)
  papa evolve pr        — цикл + PR в Gitea

Использование из papa.py:
  from lib.cli_evolve import handle_evolve_command
  handle_evolve_command(args, project_root)
"""

import os
import sys
import json


def handle_evolve_command(args: list, project_root: str):
    """Обработчик CLI: papa evolve <subcommand>"""
    from lib.evolve_engine import EvolveEngine

    engine = EvolveEngine(project_root)
    subcommand = args[0] if args else "analyze"

    if subcommand == "analyze":
        result = engine.analyze()
        print("╔═══════════════════════════════════════════╗")
        print("║  PAPA Self-Evolving — Codebase Analysis   ║")
        print("╚═══════════════════════════════════════════╝")
        print()
        print(f"  📁 Files:      {result['total_files']}")
        print(f"  📝 Lines:      {result['total_lines']}")
        print(f"  🔧 Functions:  {result['total_functions']}")
        print(f"  📏 Avg size:   {result['avg_file_size']} lines/file")
        print(f"  🔄 Duplicates: {result['duplicated_patterns']} patterns")
        print(f"  📦 Stdlib:     {len(result['stdlib_modules'])} modules")
        print(f"  ⚠️  Unused:    {', '.join(result['unused_modules']) or 'none'}")
        print()

        if result.get("large_files"):
            print("  Large files (>100 lines):")
            for lf in result["large_files"][:5]:
                print(f"    {lf['file']}: {lf['lines']} lines")
            print()

        if result.get("files_with_todos"):
            print("  Files with TODO/FIXME:")
            for f in result["files_with_todos"][:5]:
                print(f"    {f}")
            print()

        print("  Top 5 modules by usage:")
        for mod, count in list(result.get("most_used_modules", {}).items())[:5]:
            print(f"    {mod}: {count} imports")

        # Сохраняем JSON для suggest
        report_path = os.path.join(project_root, ".papa-evolve-analysis.json")
        with open(report_path, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n  Full report: {report_path}")

    elif subcommand == "suggest":
        print("🤖 Generating suggestions...")
        print()
        suggestions = engine.suggest()
        if not suggestions:
            print("  No suggestions. Codebase is clean! 🎉")
            return

        for i, s in enumerate(suggestions, 1):
            icon = {"refactor": "🔄", "cleanup": "🧹", "documentation": "📝",
                    "structure": "📦", "new_stdlib": "⭐", "incomplete": "⚠️"}.get(s["type"], "💡")
            prio = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(s.get("priority", ""), "⚪")
            print(f"  {icon} {prio} [{s['id']}] {s['description']}")
            if s.get("confidence"):
                print(f"     Confidence: {s['confidence']*100:.0f}%")
            print()

        print(f"  Total: {len(suggestions)} suggestions")

    elif subcommand == "run":
        result = engine.run()
        print()
        print("═══════════════════════════════════════════")
        print(f"  Status: {result['status']}")
        print(f"  Created: {len(result['created'])} modules")
        print(f"  Tests: {result['tests']['passed']} passed, {result['tests']['failures']} failed")
        print("═══════════════════════════════════════════")

    elif subcommand == "pr":
        gitea_url = os.environ.get("GITEA_URL", "https://git.papa-ai.ae")
        gitea_token = os.environ.get("GITEA_TOKEN", "")
        if not gitea_token:
            print("⚠️  GITEA_TOKEN not set. Will create branch only (no PR).")
        result = engine.pr(gitea_url, gitea_token)
        print(result)

    else:
        print("Usage: papa evolve [analyze|suggest|run|pr]")
        print()
        print("  analyze  — analyze codebase for patterns")
        print("  suggest  — generate improvement suggestions")
        print("  run      — full cycle: analyze → suggest → create → test → commit")
        print("  pr       — full cycle + create PR in Gitea")

# Alias for papa.py
handle_evolve = handle_evolve_command
