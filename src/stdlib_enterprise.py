"""
PAPA Lang stdlib_enterprise — orchestrator, docs, studio, cwb.
"""

import time
from typing import Any, Dict

from .environment import PapaList, PapaMap


def _load_orchestrator(interp: 'Interpreter') -> Dict[str, Any]:
    """Orchestrator module: AI safety layer for development tasks"""
    orc_log_history = []
    ARCHITECTURE_RULES = {
        "protected_files": [
            "src/interpreter.py", "src/lexer.py", "src/parser.py", "src/ast_nodes.py",
            "papa.py", "middleware.ts", "lib/auth.ts",
        ],
        "protected_patterns": ["SECRET", "RBAC", "ai_budget", "voice_config"],
        "module_boundaries": {
            "papa-lang": ["src/", "std/", "examples/", "showcase/", "enterprise/"],
            "papa-shared": ["app/", "components/", "lib/", "papa-finance/", "papa-life/", "papa-docs/"],
            "papa-devops": ["papa-lang-site/", "docker-compose.yml"],
            "papa-nexus": ["api/", "events/", "auth/"],
            "papa-ras": ["agents/", "scoring/", "models/"],
            "papa-legal": ["sanctions/", "aml/", "compliance/"],
        },
        "forbidden_actions": [
            "delete .git", "rm -rf /", "drop database", "remove auth",
            "disable security", "expose secret", "skip validation",
        ],
        "max_files_per_change": 15,
        "max_lines_per_file": 2000,
    }

    def _unwrap(a):
        return a[0]._items if a and hasattr(a[0], '_items') else (a or [])

    def _log_decision(task, decision, reasoning, risk):
        entry = PapaMap([
            ("timestamp", time.strftime("%Y-%m-%d %H:%M:%S")),
            ("task", str(task)[:100]),
            ("decision", decision),
            ("reasoning", str(reasoning)[:200]),
            ("risk_level", risk),
        ])
        orc_log_history.append(entry)
        return entry

    def _analyze_risk(task_text, context=None):
        task_lower = task_text.lower()
        risk = "low"
        issues = []
        recommendations = []
        modules = []
        for forbidden in ARCHITECTURE_RULES["forbidden_actions"]:
            if forbidden.lower() in task_lower:
                risk = "critical"
                issues.append(f"Forbidden action detected: '{forbidden}'")
        for pf in ARCHITECTURE_RULES["protected_files"]:
            if pf.lower() in task_lower:
                if any(w in task_lower for w in ["delete", "remove", "rewrite", "replace all"]):
                    risk = "high"
                    issues.append(f"Dangerous action on protected file: {pf}")
                    recommendations.append(f"Use str_replace for surgical edits to {pf}, not full rewrites")
                elif any(w in task_lower for w in ["modify", "edit", "update", "add"]):
                    risk = "medium"
                    recommendations.append(f"Protected file {pf}: make minimal, targeted changes only")
        for pp in ARCHITECTURE_RULES["protected_patterns"]:
            if pp.lower() in task_lower and any(w in task_lower for w in ["remove", "disable", "skip", "bypass"]):
                risk = "critical"
                issues.append(f"Attempt to weaken security pattern: {pp}")
        if any(w in task_lower for w in ["rewrite entire", "rebuild from scratch", "replace all", "complete overhaul"]):
            risk = "high" if risk != "critical" else risk
            issues.append("Large-scale rewrite requested")
            recommendations.append("Break into smaller incremental changes")
        for mod_name in ARCHITECTURE_RULES["module_boundaries"]:
            if mod_name.lower() in task_lower:
                modules.append(mod_name)
        if len(modules) > 2:
            risk = "medium" if risk not in ["high", "critical"] else risk
            issues.append(f"Cross-module change affecting {len(modules)} modules")
            recommendations.append("Test each module independently")
        if not recommendations:
            recommendations.append("Proceed with standard precautions")
        return risk, issues, recommendations, modules

    def orc_config(args):
        a = _unwrap(args)
        api_key = a[0] if len(a) > 0 else None
        model = str(a[1]) if len(a) > 1 else "claude-sonnet-4-20250514"
        if api_key and hasattr(api_key, '_raw_value'):
            api_key = api_key._raw_value
        if api_key and hasattr(api_key, 'raw'):
            api_key = api_key.raw
        interp.global_env.set('__orc_api_key', api_key)
        interp.global_env.set('__orc_model', model)
        return PapaMap([
            ("status", "configured"), ("model", model),
            ("rules_loaded", len(ARCHITECTURE_RULES["protected_files"])),
            ("forbidden_actions", len(ARCHITECTURE_RULES["forbidden_actions"])),
        ])

    def orc_review(args):
        a = _unwrap(args)
        task = str(a[0]) if len(a) > 0 else ""
        risk, issues, recommendations, modules = _analyze_risk(task)
        if risk == "critical":
            decision, reasoning = "reject", f"BLOCKED: {'; '.join(issues)}"
        elif risk == "high":
            decision, reasoning = "modify", f"High risk: {'; '.join(issues)}. Apply recommendations."
        elif risk == "medium":
            decision, reasoning = "modify", f"Medium risk: {'; '.join(issues)}. Consider recommendations."
        else:
            decision, reasoning = "approve", "No architectural risks detected. Proceed."
        _log_decision(task, decision, reasoning, risk)
        return PapaMap([
            ("decision", decision), ("risk_level", risk), ("reasoning", reasoning),
            ("issues_count", len(issues)), ("issues", "; ".join(issues) if issues else "none"),
            ("recommendations", "; ".join(recommendations)),
            ("modules_affected", ", ".join(modules) if modules else "none"),
        ])

    def orc_check_file(args):
        a = _unwrap(args)
        action = str(a[0]) if len(a) > 0 else "modify"
        filepath = str(a[1]) if len(a) > 1 else ""
        changes = str(a[2]) if len(a) > 2 else ""
        risk, decision, reasoning = "low", "approve", ""
        for pf in ARCHITECTURE_RULES["protected_files"]:
            if pf in filepath:
                if action == "delete":
                    risk, decision, reasoning = "critical", "reject", f"CANNOT delete protected file: {pf}"
                elif action == "create":
                    risk, decision, reasoning = "low", "approve", "Creating new file OK"
                else:
                    risk, decision, reasoning = "medium", "modify", f"Protected file {pf}: use surgical edits only"
                break
        if not reasoning:
            if action == "delete":
                risk, decision, reasoning = "medium", "modify", f"Deletion of {filepath}: verify no deps"
            elif action == "move":
                risk, decision, reasoning = "medium", "modify", f"Moving {filepath}: update imports"
            else:
                decision, reasoning = "approve", f"{action} on {filepath}: no issues"
        _log_decision(f"{action} {filepath}", decision, reasoning, risk)
        return PapaMap([("decision", decision), ("risk_level", risk), ("reasoning", reasoning),
            ("action", action), ("filepath", filepath)])

    def orc_check_arch(args):
        a = _unwrap(args)
        description = str(a[0]) if len(a) > 0 else ""
        affected = a[1] if len(a) > 1 else PapaList([])
        modules_list = [str(m) for m in affected._items] if hasattr(affected, '_items') else []
        risk, issues, recs, _ = _analyze_risk(description)
        if len(modules_list) > 3:
            risk = "high"
            issues.append(f"Affects {len(modules_list)} modules simultaneously")
            recs.append("Split into per-module PRs")
        decision = "reject" if risk == "critical" else "modify" if risk in ["high", "medium"] else "approve"
        _log_decision(description, decision, "; ".join(issues) or "ok", risk)
        return PapaMap([
            ("decision", decision), ("risk_level", risk), ("modules_affected", len(modules_list)),
            ("issues", "; ".join(issues) if issues else "none"),
            ("recommendations", "; ".join(recs)),
            ("boundary_violations", 0),
        ])

    def orc_check_deps(args):
        a = _unwrap(args)
        action = str(a[0]) if len(a) > 0 else "install"
        packages = a[1] if len(a) > 1 else PapaList([])
        pkg_list = [str(p) for p in packages._items] if hasattr(packages, '_items') else []
        risk, issues = "low", []
        if action == "remove":
            risk, issues = "medium", [f"Removing {len(pkg_list)} packages — verify no imports"]
        elif action == "update" and len(pkg_list) > 5:
            risk, issues = "medium", [f"Bulk update of {len(pkg_list)} packages — test after"]
        decision = "modify" if risk != "low" else "approve"
        _log_decision(f"deps {action}", decision, "; ".join(issues) or "ok", risk)
        return PapaMap([
            ("decision", decision), ("risk_level", risk), ("action", action),
            ("packages_count", len(pkg_list)), ("issues", "; ".join(issues) if issues else "none"),
        ])

    def orc_validate_prompt(args):
        a = _unwrap(args)
        prompt = str(a[0]) if len(a) > 0 else ""
        risk, issues, recs, modules = _analyze_risk(prompt)
        prompt_size = len(prompt.split())
        if prompt_size > 500:
            issues.append("Very large prompt — consider splitting")
            risk = "medium" if risk == "low" else risk
        decision = "reject" if risk == "critical" else "modify" if risk in ["high", "medium"] else "approve"
        _log_decision(f"prompt validation ({prompt_size} words)", decision, "; ".join(issues) or "ok", risk)
        return PapaMap([
            ("decision", decision), ("risk_level", risk), ("prompt_words", prompt_size),
            ("issues_count", len(issues)), ("issues", "; ".join(issues) if issues else "none"),
            ("recommendations", "; ".join(recs)),
            ("modules_affected", ", ".join(modules) if modules else "none"),
        ])

    def orc_log(args):
        return PapaList(orc_log_history)

    def orc_verify(args):
        a = _unwrap(args)
        task = str(a[0]) if len(a) > 0 else ""
        plan_val = a[1] if len(a) > 1 else None
        plan_text = ""
        if plan_val:
            if hasattr(plan_val, '_data'):
                plan_text = str(plan_val._data)
            elif hasattr(plan_val, '_items'):
                plan_text = str(plan_val._items)
            else:
                plan_text = str(plan_val)
        errors = []
        if not task:
            errors.append("task is empty")
        if not plan_text:
            errors.append("plan is empty")
        task_words = set(task.lower().split())
        plan_lower = plan_text.lower()
        if "protected" in task_words or "interpreter" in task_words:
            if "delete" in plan_lower or "rewrite" in plan_lower:
                errors.append("Plan touches protected areas with destructive action")
        if "secret" in task_words and "expose" in plan_lower:
            errors.append("Plan may expose secrets")
        ok = len(errors) == 0
        _log_decision(f"verify: {task[:50]}...", "approve" if ok else "modify",
            "ok" if ok else "; ".join(errors), "low" if ok else "medium")
        return PapaMap([
            ("ok", ok), ("errors_count", len(errors)), ("errors", "; ".join(errors) if errors else ""),
            ("task_excerpt", task[:80]), ("plan_excerpt", plan_text[:80]),
        ])

    def orc_autofix(args):
        a = _unwrap(args)
        task = str(a[0]) if len(a) > 0 else ""
        plan_val = a[1] if len(a) > 1 else None
        errors_val = a[2] if len(a) > 2 else PapaList([])
        errors_list = [str(e) for e in errors_val._items] if hasattr(errors_val, '_items') else []
        suggestions = []
        for e in errors_list:
            if "empty" in e.lower():
                suggestions.append("Provide non-empty task and plan")
            elif "protected" in e.lower():
                suggestions.append("Use str_replace for surgical edits instead of full rewrites")
            elif "secret" in e.lower():
                suggestions.append("Keep secrets in Secret type, never log or expose")
            else:
                suggestions.append("Review and adjust plan to address: " + e)
        if not suggestions:
            suggestions.append("No fixes needed")
        return PapaMap([
            ("fixed", len(errors_list) == 0), ("suggestions_count", len(suggestions)),
            ("suggestions", "; ".join(suggestions)),
            ("task_excerpt", task[:80]),
        ])

    def orc_cycle(args):
        a = _unwrap(args)
        task = str(a[0]) if len(a) > 0 else ""
        max_steps = int(a[1]) if len(a) > 1 else 3
        steps_done = 0
        last_decision = "approve"
        last_review = PapaMap([("decision", "approve"), ("risk_level", "low")])
        while steps_done < max_steps:
            steps_done += 1
            rev = orc_review([task])
            last_review = rev
            last_decision = rev._data.get("decision", "approve")
            if last_decision == "reject":
                break
            if last_decision == "approve":
                break
        return PapaMap([
            ("steps", steps_done), ("final_decision", last_decision),
            ("last_review", last_review), ("task_excerpt", task[:80]),
        ])

    prefix = "_orc_"
    for fn in (orc_config, orc_review, orc_check_file, orc_check_arch, orc_check_deps,
               orc_validate_prompt, orc_log, orc_verify, orc_autofix, orc_cycle):
        interp.builtins[prefix + fn.__name__] = fn
    return {k: ("builtin", prefix + k) for k in ["orc_config", "orc_review", "orc_check_file",
        "orc_check_arch", "orc_check_deps", "orc_validate_prompt", "orc_log",
        "orc_verify", "orc_autofix", "orc_cycle"]}


def _load_docs(interp: 'Interpreter') -> Dict[str, Any]:
    prefix = "_docs_"

    def docs_brand(args):
        name = str(args[0]) if args else "Company"
        colors = PapaMap([("primary", "#2563EB"), ("secondary", "#64748B"), ("accent", "#F59E0B")])
        return PapaMap([("name", name), ("tagline", f"{name} — trusted solutions"),
            ("colors", colors), ("fonts", "Inter, Georgia")])

    def docs_logo(args):
        name = str(args[0]) if args else "Brand"
        return PapaMap([("text", name[:2].upper()), ("svg_snippet", f'<text>{name[:2]}</text>'),
            ("suggestions", PapaList(["monogram", "icon", "wordmark"]))])

    def docs_generate(args):
        template = str(args[0]) if args else "letter"
        data_val = args[1] if len(args) > 1 else PapaMap([])
        data = data_val._data if hasattr(data_val, '_data') else {}
        content = f"Document: {template}\n"
        for k, v in data.items():
            content += f"{k}: {v}\n"
        return PapaMap([("content", content), ("template", template), ("word_count", len(content.split()))])

    def docs_templates(args):
        return PapaList([
            PapaMap([("id", "letter"), ("name", "Official Letter"), ("fields", "recipient,sender,date,body")]),
            PapaMap([("id", "report"), ("name", "Report"), ("fields", "title,date,sections,summary")]),
            PapaMap([("id", "contract"), ("name", "Contract"), ("fields", "parties,terms,date,signatures")]),
        ])

    def docs_preview_letterhead(args):
        brand_val = args[0] if args else PapaMap([])
        brand = brand_val._data if hasattr(brand_val, '_data') else {}
        name = brand.get("name", "Company")
        return PapaMap([("html", f'<header>{name}</header>'), ("css", "header { font-size: 24px; }")])

    for fn in (docs_brand, docs_logo, docs_generate, docs_templates, docs_preview_letterhead):
        interp.builtins[prefix + fn.__name__] = fn
    return {k: ("builtin", prefix + k) for k in ["docs_brand", "docs_logo", "docs_generate",
        "docs_templates", "docs_preview_letterhead"]}


def _load_studio(interp: 'Interpreter') -> Dict[str, Any]:
    prefix = "_studio_"

    def studio_analyze(args):
        desc = str(args[0]) if args else ""
        tasks = []
        if "api" in desc.lower():
            tasks.append(PapaMap([("type", "backend"), ("name", "API"), ("estimate", "2h")]))
        if "ui" in desc.lower() or "form" in desc.lower():
            tasks.append(PapaMap([("type", "frontend"), ("name", "UI"), ("estimate", "3h")]))
        if not tasks:
            tasks.append(PapaMap([("type", "unknown"), ("name", "Task"), ("estimate", "1h")]))
        return PapaMap([("tasks", PapaList(tasks)), ("complexity", "medium"),
            ("description_excerpt", desc[:100])])

    def studio_structure(args):
        project_type = str(args[0]) if args else "web"
        structures = {
            "web": PapaList(["src/", "public/", "package.json"]),
            "api": PapaList(["api/", "lib/", "routes/"]),
            "cli": PapaList(["cmd/", "pkg/", "main.go"]),
        }
        return PapaMap([("folders", structures.get(project_type, structures["web"])),
            ("project_type", project_type)])

    def studio_estimate(args):
        tasks_val = args[0] if args else PapaList([])
        tasks = tasks_val._items if hasattr(tasks_val, '_items') else []
        total = 0
        for t in tasks:
            est = "1h"
            if hasattr(t, '_data'):
                est = t._data.get("estimate", "1h")
            elif isinstance(t, dict):
                est = t.get("estimate", "1h")
            try:
                total += int(str(est).replace("h", ""))
            except ValueError:
                total += 1
        return PapaMap([("total_hours", total), ("tasks_count", len(tasks)), ("buffer", total // 4)])

    for fn in (studio_analyze, studio_structure, studio_estimate):
        interp.builtins[prefix + fn.__name__] = fn
    return {k: ("builtin", prefix + k) for k in ["studio_analyze", "studio_structure", "studio_estimate"]}


def _load_cwb(interp: 'Interpreter') -> Dict[str, Any]:
    """CWB: AI-помощник для мобильных задач."""
    prefix = "_cwb_"
    cwb_ideas_store = []
    cwb_tasks_store = []
    cwb_context_store = {}

    def cwb_process(args):
        text = str(args[0]) if args else ""
        words = text.split()
        intent = "unknown"
        if any(w in ["создать", "create", "добавить", "add"] for w in words):
            intent = "create"
        elif any(w in ["найти", "find", "показать", "show", "list"] for w in words):
            intent = "query"
        elif any(w in ["удалить", "delete", "убрать"] for w in words):
            intent = "delete"
        elif any(w in ["выполнить", "execute", "запустить"] for w in words):
            intent = "execute"
        return PapaMap([
            ("intent", intent), ("words_count", len(words)),
            ("suggestions", PapaList(["create", "query", "execute"])),
        ])

    def cwb_idea(args):
        idea = str(args[0]) if args else ""
        cwb_ideas_store.append(idea)
        return PapaMap([("id", len(cwb_ideas_store)), ("text", idea[:100]), ("status", "saved")])

    def cwb_ideas_list(args):
        return PapaList([PapaMap([("id", i + 1), ("text", t[:80])]) for i, t in enumerate(cwb_ideas_store)])

    def cwb_command(args):
        cmd = str(args[0]) if args else ""
        parsed = cwb_process([cmd])
        return PapaMap([("raw", cmd), ("intent", parsed._data.get("intent", "unknown")),
            ("confidence", 0.85), ("executable", True)])

    def cwb_task_add(args):
        title = str(args[0]) if args else ""
        due_val = args[1] if len(args) > 1 else ""
        cwb_tasks_store.append({"title": title, "due": str(due_val), "done": False})
        return PapaMap([("id", len(cwb_tasks_store)), ("title", title[:80]), ("status", "added")])

    def cwb_task_list(args):
        return PapaList([
            PapaMap([("id", i + 1), ("title", t["title"][:60]), ("done", t["done"])])
            for i, t in enumerate(cwb_tasks_store)
        ])

    def cwb_task_done(args):
        task_id = int(args[0]) if args else 0
        if 1 <= task_id <= len(cwb_tasks_store):
            cwb_tasks_store[task_id - 1]["done"] = True
            return PapaMap([("id", task_id), ("status", "done")])
        return PapaMap([("id", task_id), ("status", "not_found")])

    def cwb_context(args):
        key = str(args[0]) if args else ""
        value = args[1] if len(args) > 1 else None
        if value is not None:
            cwb_context_store[key] = value
            return PapaMap([("key", key), ("status", "set")])
        v = cwb_context_store.get(key)
        return PapaMap([("key", key), ("value", v), ("status", "found" if v is not None else "missing")])

    for fn in (cwb_process, cwb_idea, cwb_ideas_list, cwb_command, cwb_task_add, cwb_task_list,
               cwb_task_done, cwb_context):
        interp.builtins[prefix + fn.__name__] = fn
    return {k: ("builtin", prefix + k) for k in ["cwb_process", "cwb_idea", "cwb_ideas_list",
        "cwb_command", "cwb_task_add", "cwb_task_list", "cwb_task_done", "cwb_context"]}


__all__ = ['_load_orchestrator', '_load_docs', '_load_studio', '_load_cwb']
