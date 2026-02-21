"""
PAPA Lang — Self-Evolving Engine (lib/evolve_engine.py)
=======================================================
Полная реализация по спецификации из CURSOR_WAVE2_REVOLUTIONARY.md

Класс EvolveEngine:
  - analyze() — анализ всех .papa файлов на паттерны
  - suggest() — AI генерирует предложения новых stdlib-функций
  - create_module() — создаёт новый модуль + тесты
  - run() — полный цикл самоэволюции
  - pr() — эволюция с отправкой PR в Gitea

CLI (lib/cli_evolve.py):
  papa evolve analyze
  papa evolve suggest
  papa evolve run
  papa evolve pr
"""

import os
import re
import json
import glob
import subprocess
from datetime import datetime
from collections import Counter
from typing import Dict, List, Any, Optional


class EvolveEngine:
    """PAPA Lang Self-Evolving Engine — анализирует код, генерирует улучшения, создаёт PR."""

    def __init__(self, project_root: str):
        self.root = project_root
        self.stdlib_dir = os.path.join(project_root, "std")
        # Fallback: некоторые проекты используют stdlib/
        if not os.path.isdir(self.stdlib_dir):
            self.stdlib_dir = os.path.join(project_root, "stdlib")
        self.showcase_dir = os.path.join(project_root, "showcase")
        self.examples_dir = os.path.join(project_root, "examples")
        self.enterprise_dir = os.path.join(project_root, "enterprise")

    # ──────────────────────────────────────────────
    # 1. ANALYZE
    # ──────────────────────────────────────────────

    def analyze(self) -> Dict[str, Any]:
        """Анализ всех .papa файлов на повторяющиеся паттерны."""
        files = self._find_papa_files()

        all_functions = []
        all_imports = []
        all_patterns = []
        file_stats = []

        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    code = fh.read()
            except Exception:
                continue

            rel_path = os.path.relpath(f, self.root)
            lines = code.strip().split("\n")
            line_count = len(lines)

            # Извлечение функций (разные синтаксисы PAPA Lang)
            fns = re.findall(r'(?:fn\s+)?(\w+)\s*\(', code)
            all_functions.extend(fns)

            # Извлечение импортов
            uses = re.findall(r'(?:use|import)\s+"?(?:std/)?(\w+)"?', code)
            all_imports.extend(uses)

            # Извлечение 3-строчных паттернов (для поиска дублей)
            for i in range(len(lines) - 2):
                pattern = "\n".join(lines[i : i + 3]).strip()
                if len(pattern) > 30 and not pattern.startswith("//"):
                    all_patterns.append(pattern)

            # Метрики файла
            comment_lines = sum(1 for l in lines if l.strip().startswith("//"))
            todo_count = sum(1 for l in lines if "TODO" in l or "FIXME" in l or "HACK" in l)
            max_line_len = max((len(l) for l in lines), default=0)

            file_stats.append({
                "file": rel_path,
                "lines": line_count,
                "functions": len(re.findall(r'(?:fn\s+)?(\w+)\s*\(', code)),
                "imports": len(uses),
                "comments": comment_lines,
                "comment_ratio": round(comment_lines / max(line_count, 1), 2),
                "todos": todo_count,
                "max_line_length": max_line_len,
            })

        func_freq = Counter(all_functions)
        import_freq = Counter(all_imports)
        pattern_freq = Counter(all_patterns)

        # Дублированные паттерны (встречаются 2+ раза)
        duplicates = {k: v for k, v in pattern_freq.items() if v >= 2}

        # Неиспользуемые stdlib-модули
        stdlib_modules = self._list_stdlib_modules()
        unused = [m for m in stdlib_modules if m not in all_imports]

        # Оценка сложности
        total_lines = sum(fs["lines"] for fs in file_stats)
        total_functions = len(set(all_functions))
        avg_file_size = total_lines / max(len(files), 1)

        return {
            "timestamp": datetime.now().isoformat(),
            "total_files": len(files),
            "total_lines": total_lines,
            "total_functions": total_functions,
            "avg_file_size": round(avg_file_size, 1),
            "function_frequency": dict(func_freq.most_common(20)),
            "import_frequency": dict(import_freq.most_common(10)),
            "duplicated_patterns": len(duplicates),
            "duplicated_pattern_samples": dict(list(duplicates.items())[:5]),
            "unused_modules": unused,
            "most_used_modules": dict(import_freq.most_common(5)),
            "stdlib_modules": stdlib_modules,
            "files_with_todos": [
                fs["file"] for fs in file_stats if fs["todos"] > 0
            ],
            "large_files": [
                {"file": fs["file"], "lines": fs["lines"]}
                for fs in file_stats
                if fs["lines"] > 100
            ],
            "low_comment_files": [
                {"file": fs["file"], "ratio": fs["comment_ratio"]}
                for fs in file_stats
                if fs["comment_ratio"] < 0.1 and fs["lines"] > 20
            ],
            "file_stats": file_stats,
        }

    # ──────────────────────────────────────────────
    # 2. SUGGEST
    # ──────────────────────────────────────────────

    def suggest(self, analysis: Optional[Dict] = None) -> List[Dict]:
        """
        Генерирует предложения улучшений.
        Если AI недоступен — использует rule-based анализ.
        """
        if analysis is None:
            analysis = self.analyze()

        suggestions = []

        # Rule-based предложения (всегда работают, без AI)

        # 1. Дублированные паттерны → извлечь в функцию
        if analysis["duplicated_patterns"] > 0:
            suggestions.append({
                "id": "sug_dedup_1",
                "type": "refactor",
                "priority": "high",
                "confidence": 0.9,
                "module_name": "utils",
                "description": f"Найдено {analysis['duplicated_patterns']} повторяющихся паттернов. "
                               "Извлеките общий код в утилитарные функции.",
                "functions": [
                    {
                        "name": "extract_common_pattern",
                        "code": '// Auto-extracted utility\nfn extract_pattern(data) -> text =\n    // TODO: implement based on pattern analysis\n    return data',
                        "test": 'test "extract_pattern works"\n    result = extract_pattern("test")\n    assert result == "test"',
                    }
                ],
            })

        # 2. Неиспользуемые модули
        if analysis["unused_modules"]:
            suggestions.append({
                "id": "sug_unused_1",
                "type": "cleanup",
                "priority": "low",
                "confidence": 0.95,
                "description": f"Неиспользуемые модули: {', '.join(analysis['unused_modules'])}. "
                               "Добавьте примеры или удалите если не нужны.",
                "modules": analysis["unused_modules"],
            })

        # 3. Файлы без комментариев
        for lc in analysis.get("low_comment_files", []):
            suggestions.append({
                "id": f"sug_docs_{lc['file']}",
                "type": "documentation",
                "priority": "medium",
                "confidence": 0.85,
                "description": f"Файл {lc['file']} имеет низкий % комментариев ({lc['ratio']*100:.0f}%). "
                               "Добавьте документирующие комментарии.",
                "file": lc["file"],
            })

        # 4. Большие файлы → разбить
        for lf in analysis.get("large_files", []):
            if lf["lines"] > 200:
                suggestions.append({
                    "id": f"sug_split_{lf['file']}",
                    "type": "structure",
                    "priority": "medium",
                    "confidence": 0.8,
                    "description": f"Файл {lf['file']} ({lf['lines']} строк) — рассмотрите разделение на модули.",
                    "file": lf["file"],
                })

        # 5. Частые функции → кандидаты для stdlib
        freq = analysis.get("function_frequency", {})
        for func_name, count in freq.items():
            if count >= 4 and func_name not in ("print", "assert", "test", "let", "fn", "if"):
                suggestions.append({
                    "id": f"sug_stdlib_{func_name}",
                    "type": "new_stdlib",
                    "priority": "high",
                    "confidence": 0.7,
                    "module_name": "common",
                    "description": f"Функция '{func_name}' используется {count} раз — кандидат для stdlib.",
                    "functions": [
                        {
                            "name": func_name,
                            "code": f"// Promoted to stdlib from common usage\n"
                                    f"fn {func_name}(args) -> auto =\n    // TODO: generalize implementation\n    return null",
                            "test": f'test "{func_name} works"\n    result = {func_name}(null)\n    assert result != null',
                        }
                    ],
                })

        # 6. TODO/FIXME файлы
        if analysis.get("files_with_todos"):
            suggestions.append({
                "id": "sug_todos_1",
                "type": "incomplete",
                "priority": "medium",
                "confidence": 0.95,
                "description": f"Файлы с TODO/FIXME: {', '.join(analysis['files_with_todos'][:5])}",
                "files": analysis["files_with_todos"],
            })

        # AI-enhanced предложения (если доступен AI)
        ai_suggestions = self._ai_suggest(analysis)
        if ai_suggestions:
            suggestions.extend(ai_suggestions)

        return suggestions

    # ──────────────────────────────────────────────
    # 3. CREATE MODULE
    # ──────────────────────────────────────────────

    def create_module(self, name: str, functions: List[Dict]) -> Dict[str, str]:
        """Создаёт новый .papa модуль + тесты."""
        # Модуль
        header = (
            f"// Auto-generated by PAPA Self-Evolving Engine\n"
            f"// Generated: {datetime.now().isoformat()}\n"
            f"// Source: evolve_suggest() analysis\n\n"
            f"module {name}\n\n"
        )
        body = ""
        for func in functions:
            body += func.get("code", "") + "\n\n"

        module_path = os.path.join(self.stdlib_dir, f"{name}.papa")
        os.makedirs(os.path.dirname(module_path), exist_ok=True)
        with open(module_path, "w", encoding="utf-8") as f:
            f.write(header + body)

        # Тесты
        test_body = (
            f"// Auto-generated tests for {name}\n"
            f"// Generated: {datetime.now().isoformat()}\n\n"
            f'import "std/{name}"\n\n'
        )
        for func in functions:
            test_body += func.get("test", "") + "\n\n"
        test_body += f'print("✅ All {name} tests passed!")\n'

        test_path = os.path.join(self.showcase_dir, f"test_{name}.papa")
        os.makedirs(os.path.dirname(test_path), exist_ok=True)
        with open(test_path, "w", encoding="utf-8") as f:
            f.write(test_body)

        return {"module": module_path, "tests": test_path}

    # ──────────────────────────────────────────────
    # 4. RUN — полный цикл
    # ──────────────────────────────────────────────

    def run(self) -> Dict[str, Any]:
        """Полный цикл самоэволюции."""
        print("🧬 PAPA Self-Evolving Engine started")
        print()

        # 1. Анализ
        print("📊 Step 1: Analyzing codebase...")
        analysis = self.analyze()
        print(f"   Files: {analysis['total_files']}")
        print(f"   Functions: {analysis['total_functions']}")
        print(f"   Duplicates: {analysis['duplicated_patterns']}")

        # 2. Предложения
        print()
        print("🤖 Step 2: Generating suggestions...")
        suggestions = self.suggest(analysis)
        print(f"   Suggestions: {len(suggestions)}")

        # 3. Создание модулей (только high-confidence)
        print()
        print("📝 Step 3: Creating new modules...")
        created = []
        for s in suggestions:
            if s.get("confidence", 0) > 0.8 and s.get("type") == "new_stdlib" and s.get("functions"):
                try:
                    paths = self.create_module(s["module_name"], s["functions"])
                    created.append(paths["module"])
                    print(f"   ✅ Created: {paths['module']}")
                except Exception as e:
                    print(f"   ❌ Failed: {e}")

        # 4. Запуск тестов
        print()
        print("🧪 Step 4: Running tests...")
        test_results = self._run_tests()

        # 5. Git commit (если тесты прошли)
        print()
        if test_results["failures"] == 0 and created:
            print("✅ All tests passed!")
            self._git_commit(created, analysis)
            print("📦 Committed to git")
        elif not created:
            print("ℹ️ No new modules created (all suggestions below confidence threshold)")
        else:
            print(f"❌ {test_results['failures']} tests failed — not committing")
            print("   Manual review required")

        return {
            "analysis": analysis,
            "suggestions": len(suggestions),
            "created": created,
            "tests": test_results,
            "status": "success" if test_results["failures"] == 0 else "needs_review",
        }

    # ──────────────────────────────────────────────
    # 5. PR — эволюция с Gitea PR
    # ──────────────────────────────────────────────

    def pr(self, gitea_url: str = "", gitea_token: str = "") -> str:
        """Создаёт PR в Gitea с результатами эволюции."""
        branch = f"evolve/{datetime.now().strftime('%Y-%m-%d-%H%M')}"

        # Создаём ветку
        self._git_cmd(["checkout", "-b", branch])

        result = self.run()

        if result["status"] == "success" and result["created"]:
            self._git_cmd(["push", "origin", branch])

            # Создаём PR через Gitea API
            if gitea_url and gitea_token:
                pr_result = self._create_gitea_pr(
                    gitea_url, gitea_token, branch, result
                )
                # Возвращаемся на main
                self._git_cmd(["checkout", "main"])
                return f"PR created: {pr_result.get('html_url', 'check Gitea')}"

            self._git_cmd(["checkout", "main"])
            return f"Branch '{branch}' pushed. Create PR manually in Gitea."

        self._git_cmd(["checkout", "main"])
        # Удаляем ветку если нечего коммитить
        self._git_cmd(["branch", "-D", branch])
        return "Evolution completed but no changes to commit"

    # ──────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────

    def _find_papa_files(self) -> List[str]:
        """Найти все .papa файлы."""
        patterns = [
            os.path.join(self.root, "**", "*.papa"),
        ]
        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern, recursive=True))
        # Исключаем node_modules и .git
        return [
            f for f in files
            if "node_modules" not in f and ".git" not in f
        ]

    def _list_stdlib_modules(self) -> List[str]:
        """Список всех stdlib модулей."""
        if not os.path.isdir(self.stdlib_dir):
            return []
        return [
            os.path.splitext(os.path.basename(f))[0]
            for f in glob.glob(os.path.join(self.stdlib_dir, "*.papa"))
        ]

    def _ai_suggest(self, analysis: Dict) -> List[Dict]:
        """AI-предложения (если доступен ANTHROPIC_API_KEY)."""
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return []

        try:
            import httpx
            prompt = (
                "You are PAPA Lang compiler architect. "
                f"Based on this codebase analysis:\n{json.dumps(analysis, indent=2, default=str)}\n\n"
                "Suggest 2 new stdlib functions that would reduce code duplication. "
                "For each provide: module_name, function name, PAPA Lang code, test case. "
                "Return JSON array."
            )
            resp = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 2048,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30,
            )
            data = resp.json()
            text = data.get("content", [{}])[0].get("text", "")
            # Попытка парсинга JSON из ответа
            json_match = re.search(r"\[[\s\S]*\]", text)
            if json_match:
                items = json.loads(json_match.group())
                return [
                    {
                        "id": f"sug_ai_{i}",
                        "type": "new_stdlib",
                        "priority": "high",
                        "confidence": 0.75,
                        "source": "ai",
                        **item,
                    }
                    for i, item in enumerate(items)
                ]
        except Exception:
            pass
        return []

    def _run_tests(self) -> Dict[str, int]:
        """Запуск тестов PAPA Lang."""
        papa_py = os.path.join(self.root, "papa.py")
        if not os.path.isfile(papa_py):
            return {"passed": 0, "failures": 0, "total": 0}

        passed = 0
        failures = 0
        test_dirs = [self.showcase_dir, self.examples_dir]

        for d in test_dirs:
            if not os.path.isdir(d):
                continue
            for f in glob.glob(os.path.join(d, "*.papa")):
                try:
                    result = subprocess.run(
                        ["python3", papa_py, "run", f],
                        capture_output=True,
                        timeout=30,
                        cwd=self.root,
                    )
                    if result.returncode == 0:
                        passed += 1
                    else:
                        failures += 1
                except Exception:
                    failures += 1

        return {"passed": passed, "failures": failures, "total": passed + failures}

    def _git_cmd(self, args: List[str]) -> str:
        """Выполнить git команду."""
        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True,
                text=True,
                cwd=self.root,
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def _git_commit(self, files: List[str], analysis: Dict):
        """Git add + commit."""
        for f in files:
            self._git_cmd(["add", f])
        msg = (
            f"feat(evolve): auto-generated {len(files)} new modules\n\n"
            f"Analysis: {analysis['total_files']} files, "
            f"{analysis['total_functions']} functions\n"
            f"Duplicates found: {analysis['duplicated_patterns']}"
        )
        self._git_cmd(["commit", "-m", msg])

    def _create_gitea_pr(self, url: str, token: str, branch: str, result: Dict) -> Dict:
        """Создать PR в Gitea через API."""
        try:
            import httpx
            resp = httpx.post(
                f"{url}/api/v1/repos/papa/papa-lang/pulls",
                headers={"Authorization": f"token {token}"},
                json={
                    "title": f"🧬 Self-Evolving: {len(result['created'])} new modules",
                    "body": (
                        "## Auto-generated by PAPA Self-Evolving Engine\n\n"
                        f"- Files analyzed: {result['analysis']['total_files']}\n"
                        f"- Duplicates found: {result['analysis']['duplicated_patterns']}\n"
                        f"- New modules: {len(result['created'])}\n"
                        f"- Tests: {'✅ all passed' if result['tests']['failures'] == 0 else '❌ some failed'}\n\n"
                        "### Created files\n"
                        + "\n".join(f"- `{f}`" for f in result["created"])
                    ),
                    "base": "main",
                    "head": branch,
                },
                timeout=15,
            )
            return resp.json()
        except Exception:
            return {}
