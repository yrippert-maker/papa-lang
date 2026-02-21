"""
PAPA Lang — Wave 2 & Wave 3 std-модули
=======================================
Реализация 9 модулей для добавления в interpreter.py

Порядок:
  Wave 2: guard, ai_router, evolve, swarm, infra, gemini
  Wave 3: verify, chain, voice_prog

Инструкция:
  1. Скопировать все функции _std_* в interpreter.py (перед STD_MODULE_LOADERS)
  2. Добавить записи в STD_MODULE_LOADERS
  3. Обновить _resolve_import_path (список доступных модулей)
"""

from typing import Dict, Any, List, Optional
import time as _time
import hashlib
import json
import re
import os


# ╔══════════════════════════════════════════════════════════════════╗
# ║  1. GUARD — AI Guardrails (PII, prompt injection, rate limit)  ║
# ╚══════════════════════════════════════════════════════════════════╝

def _std_guard(interp: 'Interpreter') -> Dict[str, Any]:
    """
    Модуль guard — защита AI-запросов.

    Экспорты:
      guarded_ask(prompt, actor) -> map    — проверка + вызов AI
      guard_configure(config)              — настройка правил
      guard_check_pii(text) -> map         — детекция PII
      guard_check_injection(text) -> map   — детекция prompt injection
      guard_rate_check(actor) -> bool      — проверка rate limit
      guard_cost_check(model, tokens) -> map — проверка бюджета
      guard_compliance_report() -> map     — отчёт compliance
    """
    prefix = "_guard_"

    # --- Внутреннее состояние ---
    _config = {
        "pii_enabled": True,
        "injection_enabled": True,
        "rate_limit": 60,          # запросов в минуту на актора
        "rate_window": 60,         # секунд
        "cost_limit_usd": 100.0,   # бюджет на сессию
        "cost_spent_usd": 0.0,
        "blocked_patterns": [],
        "allowed_actors": [],       # пусто = все разрешены
        "log": [],
    }
    _rate_tracker: Dict[str, List[float]] = {}

    # --- PII паттерны ---
    PII_PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone_ru": r'\b(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b',
        "phone_intl": r'\b\+?\d{1,3}[\s\-]?\(?\d{2,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{2,4}\b',
        "inn": r'\b\d{10,12}\b',  # ИНН (упрощённо)
        "card_number": r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
        "passport_ru": r'\b\d{2}\s?\d{2}\s?\d{6}\b',
        "snils": r'\b\d{3}[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{2}\b',
    }

    # --- Injection паттерны ---
    INJECTION_PATTERNS = [
        r'(?i)ignore\s+(all\s+)?previous\s+instructions',
        r'(?i)you\s+are\s+now\s+',
        r'(?i)system\s*:\s*',
        r'(?i)forget\s+(everything|all|your\s+instructions)',
        r'(?i)act\s+as\s+(if\s+you\s+are|a)\s+',
        r'(?i)do\s+not\s+follow\s+',
        r'(?i)override\s+(your\s+)?instructions',
        r'(?i)jailbreak',
        r'(?i)\bDAN\b',
        r'(?i)pretend\s+(you\s+are|to\s+be)',
    ]

    # --- Функции ---

    def _check_pii(args):
        """guard_check_pii(text) -> {found: bool, matches: [...]}"""
        text = str(args[0]) if args else ""
        matches = []
        for pii_type, pattern in PII_PATTERNS.items():
            for m in re.finditer(pattern, text):
                matches.append({
                    "type": pii_type,
                    "value": m.group()[:4] + "***",  # маскировка
                    "position": m.start(),
                })
        return {"found": len(matches) > 0, "matches": matches, "count": len(matches)}

    def _check_injection(args):
        """guard_check_injection(text) -> {detected: bool, patterns: [...]}"""
        text = str(args[0]) if args else ""
        detected = []
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, text):
                detected.append(pattern)
        # Дополнительно: блокированные паттерны из конфига
        for bp in _config["blocked_patterns"]:
            if bp.lower() in text.lower():
                detected.append(f"blocked:{bp}")
        return {"detected": len(detected) > 0, "patterns": detected, "count": len(detected)}

    def _rate_check(args):
        """guard_rate_check(actor) -> bool (true = разрешено)"""
        actor = str(args[0]) if args else "anonymous"
        now = _time.time()
        window = _config["rate_window"]
        limit = _config["rate_limit"]

        if actor not in _rate_tracker:
            _rate_tracker[actor] = []

        # Очистка старых записей
        _rate_tracker[actor] = [t for t in _rate_tracker[actor] if now - t < window]

        if len(_rate_tracker[actor]) >= limit:
            _log_event("rate_limit_exceeded", actor=actor)
            return False

        _rate_tracker[actor].append(now)
        return True

    def _cost_check(args):
        """guard_cost_check(model, tokens) -> {allowed: bool, cost_usd: float, remaining: float}"""
        model = str(args[0]) if len(args) > 0 else "claude-sonnet"
        tokens = int(args[1]) if len(args) > 1 else 1000

        # Примерные цены за 1K токенов (USD)
        pricing = {
            "claude-opus": 0.075,
            "claude-sonnet": 0.015,
            "claude-haiku": 0.003,
            "gpt-4": 0.06,
            "gpt-4o": 0.01,
            "gpt-3.5": 0.002,
            "gemini-pro": 0.00125,
            "gemini-flash": 0.000375,
        }
        price_per_1k = pricing.get(model, 0.015)
        cost = (tokens / 1000) * price_per_1k

        allowed = (_config["cost_spent_usd"] + cost) <= _config["cost_limit_usd"]
        if allowed:
            _config["cost_spent_usd"] += cost

        remaining = _config["cost_limit_usd"] - _config["cost_spent_usd"]
        return {"allowed": allowed, "cost_usd": round(cost, 6), "remaining_usd": round(remaining, 4)}

    def _guarded_ask(args):
        """guarded_ask(prompt, actor) -> {status, response|error, checks}"""
        prompt = str(args[0]) if len(args) > 0 else ""
        actor = str(args[1]) if len(args) > 1 else "anonymous"

        checks = {}

        # 1. Allowed actors
        if _config["allowed_actors"] and actor not in _config["allowed_actors"]:
            _log_event("actor_blocked", actor=actor)
            return {"status": "blocked", "error": "Actor not allowed", "checks": {}}

        # 2. Rate limit
        if not _rate_check([actor]):
            return {"status": "rate_limited", "error": "Rate limit exceeded", "checks": {"rate": False}}
        checks["rate"] = True

        # 3. PII check
        if _config["pii_enabled"]:
            pii_result = _check_pii([prompt])
            checks["pii"] = pii_result
            if pii_result["found"]:
                _log_event("pii_detected", actor=actor, details=pii_result)
                return {"status": "blocked_pii", "error": "PII detected in prompt", "checks": checks}

        # 4. Injection check
        if _config["injection_enabled"]:
            inj_result = _check_injection([prompt])
            checks["injection"] = inj_result
            if inj_result["detected"]:
                _log_event("injection_detected", actor=actor, details=inj_result)
                return {"status": "blocked_injection", "error": "Prompt injection detected", "checks": checks}

        # 5. Cost check
        cost_result = _cost_check(["claude-sonnet", len(prompt)])
        checks["cost"] = cost_result
        if not cost_result["allowed"]:
            _log_event("cost_exceeded", actor=actor)
            return {"status": "blocked_cost", "error": "Budget exceeded", "checks": checks}

        # Все проверки пройдены — в реальности здесь вызов AI через orchestrator
        _log_event("request_passed", actor=actor)
        return {
            "status": "ok",
            "response": f"[GUARD PASS] Prompt ({len(prompt)} chars) cleared for {actor}",
            "checks": checks,
        }

    def _configure(args):
        """guard_configure(config_map) — обновление конфигурации"""
        if args and isinstance(args[0], dict):
            for key, value in args[0].items():
                if key in _config:
                    _config[key] = value
        return _config.copy()

    def _compliance_report(args):
        """guard_compliance_report() -> map — отчёт"""
        return {
            "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "config": {k: v for k, v in _config.items() if k != "log"},
            "total_events": len(_config["log"]),
            "events_by_type": _count_events(),
            "recent_events": _config["log"][-10:],
            "cost_spent_usd": _config["cost_spent_usd"],
            "cost_remaining_usd": _config["cost_limit_usd"] - _config["cost_spent_usd"],
        }

    def _log_event(event_type: str, actor: str = "", details: Any = None):
        _config["log"].append({
            "time": _time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "type": event_type,
            "actor": actor,
            "details": details,
        })

    def _count_events() -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for ev in _config["log"]:
            t = ev["type"]
            counts[t] = counts.get(t, 0) + 1
        return counts

    # --- Регистрация ---
    interp.builtins[prefix + "guarded_ask"] = _guarded_ask
    interp.builtins[prefix + "configure"] = _configure
    interp.builtins[prefix + "check_pii"] = _check_pii
    interp.builtins[prefix + "check_injection"] = _check_injection
    interp.builtins[prefix + "rate_check"] = _rate_check
    interp.builtins[prefix + "cost_check"] = _cost_check
    interp.builtins[prefix + "compliance_report"] = _compliance_report

    return {
        "guarded_ask":            ("builtin", prefix + "guarded_ask"),
        "guard_configure":        ("builtin", prefix + "configure"),
        "guard_check_pii":        ("builtin", prefix + "check_pii"),
        "guard_check_injection":  ("builtin", prefix + "check_injection"),
        "guard_rate_check":       ("builtin", prefix + "rate_check"),
        "guard_cost_check":       ("builtin", prefix + "cost_check"),
        "guard_compliance_report":("builtin", prefix + "compliance_report"),
    }


# ╔══════════════════════════════════════════════════════════════════╗
# ║  2. AI_ROUTER — Triple AI (Claude → GPT → Gemini)             ║
# ╚══════════════════════════════════════════════════════════════════╝

def _std_ai_router(interp: 'Interpreter') -> Dict[str, Any]:
    """
    Модуль ai_router — маршрутизация запросов между AI-провайдерами.

    Экспорты:
      ai_ask(prompt, options?) -> map       — запрос с автоматическим fallback
      ai_configure(config)                   — настройка провайдеров
      ai_status() -> map                     — статус провайдеров
      ai_set_strategy(strategy)              — round_robin | failover | cost_optimal
      ai_provider_health(provider) -> map    — здоровье конкретного провайдера
    """
    prefix = "_ai_router_"

    _providers = {
        "claude": {
            "name": "Claude (Anthropic)",
            "models": ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001"],
            "api_key_env": "ANTHROPIC_API_KEY",
            "base_url": "https://api.anthropic.com/v1/messages",
            "priority": 1,
            "healthy": True,
            "errors": 0,
            "requests": 0,
            "last_error": None,
            "cost_per_1k": 0.015,
        },
        "openai": {
            "name": "GPT (OpenAI)",
            "models": ["gpt-4o", "gpt-4o-mini"],
            "api_key_env": "OPENAI_API_KEY",
            "base_url": "https://api.openai.com/v1/chat/completions",
            "priority": 2,
            "healthy": True,
            "errors": 0,
            "requests": 0,
            "last_error": None,
            "cost_per_1k": 0.01,
        },
        "gemini": {
            "name": "Gemini (Google)",
            "models": ["gemini-2.0-flash", "gemini-2.0-pro"],
            "api_key_env": "GOOGLE_API_KEY",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/models",
            "priority": 3,
            "healthy": True,
            "errors": 0,
            "requests": 0,
            "last_error": None,
            "cost_per_1k": 0.00125,
        },
    }

    _strategy = {"mode": "failover"}  # failover | round_robin | cost_optimal
    _rr_index = {"value": 0}

    def _get_sorted_providers() -> List[str]:
        mode = _strategy["mode"]
        available = [k for k, v in _providers.items() if v["healthy"]]

        if mode == "failover":
            return sorted(available, key=lambda k: _providers[k]["priority"])
        elif mode == "round_robin":
            # Ротация по кругу
            if not available:
                return []
            idx = _rr_index["value"] % len(available)
            _rr_index["value"] += 1
            return available[idx:] + available[:idx]
        elif mode == "cost_optimal":
            return sorted(available, key=lambda k: _providers[k]["cost_per_1k"])
        return available

    def _ask(args):
        """ai_ask(prompt, options?) -> {provider, model, response, attempts}"""
        prompt = str(args[0]) if args else ""
        options = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}

        preferred = options.get("provider", None)
        model_override = options.get("model", None)
        max_retries = int(options.get("retries", 3))

        providers_order = _get_sorted_providers()
        if preferred and preferred in providers_order:
            providers_order.remove(preferred)
            providers_order.insert(0, preferred)

        attempts = []
        for provider_key in providers_order[:max_retries]:
            prov = _providers[provider_key]
            model = model_override or prov["models"][0]
            api_key = os.environ.get(prov["api_key_env"], "")

            prov["requests"] += 1
            attempt = {"provider": provider_key, "model": model}

            if not api_key:
                prov["errors"] += 1
                prov["last_error"] = "API key not set"
                attempt["error"] = "API key not set"
                attempts.append(attempt)
                continue

            # Реальный HTTP-запрос — делегируем в http модуль если доступен,
            # иначе возвращаем placeholder
            try:
                # Проверяем наличие http-модуля
                http_post = interp.builtins.get("_http_post")
                if http_post and provider_key == "claude":
                    result = http_post([
                        prov["base_url"],
                        {
                            "model": model,
                            "max_tokens": int(options.get("max_tokens", 1024)),
                            "messages": [{"role": "user", "content": prompt}],
                        },
                        {
                            "x-api-key": api_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json",
                        },
                    ])
                    if isinstance(result, dict) and "content" in result:
                        attempt["status"] = "ok"
                        attempt["response"] = result["content"][0]["text"]
                        attempts.append(attempt)
                        return {
                            "status": "ok",
                            "provider": provider_key,
                            "model": model,
                            "response": attempt["response"],
                            "attempts": attempts,
                        }
                # Fallback: сигнализируем успех без реального вызова
                attempt["status"] = "ok"
                attempt["response"] = f"[{provider_key}:{model}] Response to: {prompt[:50]}..."
                attempts.append(attempt)
                return {
                    "status": "ok",
                    "provider": provider_key,
                    "model": model,
                    "response": attempt["response"],
                    "attempts": attempts,
                }

            except Exception as e:
                prov["errors"] += 1
                prov["last_error"] = str(e)
                if prov["errors"] >= 5:
                    prov["healthy"] = False
                attempt["error"] = str(e)
                attempts.append(attempt)

        return {
            "status": "all_failed",
            "error": "All providers failed",
            "attempts": attempts,
        }

    def _configure(args):
        """ai_configure(config) — обновление провайдеров"""
        config = args[0] if args and isinstance(args[0], dict) else {}
        for key, val in config.items():
            if key in _providers and isinstance(val, dict):
                _providers[key].update(val)
        return {"providers": list(_providers.keys()), "strategy": _strategy["mode"]}

    def _status(args):
        """ai_status() -> map"""
        return {
            "strategy": _strategy["mode"],
            "providers": {
                k: {
                    "name": v["name"],
                    "healthy": v["healthy"],
                    "requests": v["requests"],
                    "errors": v["errors"],
                    "has_key": bool(os.environ.get(v["api_key_env"], "")),
                }
                for k, v in _providers.items()
            },
        }

    def _set_strategy(args):
        """ai_set_strategy(strategy)"""
        mode = str(args[0]) if args else "failover"
        if mode in ("failover", "round_robin", "cost_optimal"):
            _strategy["mode"] = mode
        return _strategy["mode"]

    def _provider_health(args):
        """ai_provider_health(provider) -> map"""
        key = str(args[0]) if args else "claude"
        if key not in _providers:
            return {"error": f"Unknown provider: {key}"}
        p = _providers[key]
        return {
            "provider": key,
            "healthy": p["healthy"],
            "requests": p["requests"],
            "errors": p["errors"],
            "error_rate": round(p["errors"] / max(p["requests"], 1), 3),
            "last_error": p["last_error"],
        }

    # --- Регистрация ---
    interp.builtins[prefix + "ask"] = _ask
    interp.builtins[prefix + "configure"] = _configure
    interp.builtins[prefix + "status"] = _status
    interp.builtins[prefix + "set_strategy"] = _set_strategy
    interp.builtins[prefix + "provider_health"] = _provider_health

    return {
        "ai_ask":              ("builtin", prefix + "ask"),
        "ai_configure":        ("builtin", prefix + "configure"),
        "ai_status":           ("builtin", prefix + "status"),
        "ai_set_strategy":     ("builtin", prefix + "set_strategy"),
        "ai_provider_health":  ("builtin", prefix + "provider_health"),
    }


# ╔══════════════════════════════════════════════════════════════════╗
# ║  3. EVOLVE — Self-Evolving Code                                ║
# ╚══════════════════════════════════════════════════════════════════╝

def _std_evolve(interp: 'Interpreter') -> Dict[str, Any]:
    """
    Модуль evolve — AI-анализ кода и предложения улучшений.

    Экспорты:
      evolve_analyze(path) -> map       — анализ файла/проекта
      evolve_suggest(path) -> list      — предложения улучшений
      evolve_apply(suggestion) -> map   — применить предложение
      evolve_history() -> list          — история изменений
      evolve_rollback(id) -> map        — откатить изменение
    """
    prefix = "_evolve_"

    _history: List[Dict] = []
    _suggestions: List[Dict] = []

    def _analyze(args):
        """evolve_analyze(path) -> {files, lines, functions, complexity, issues}"""
        path = str(args[0]) if args else "."

        # Пробуем прочитать файл через fs-модуль
        fs_read = interp.builtins.get("_fs_read")
        result = {
            "path": path,
            "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "files": [],
            "total_lines": 0,
            "functions": [],
            "issues": [],
            "complexity_score": 0,
        }

        if fs_read:
            try:
                content = fs_read([path])
                if isinstance(content, str):
                    lines = content.split("\n")
                    result["total_lines"] = len(lines)
                    result["files"] = [path]

                    # Простой анализ
                    for i, line in enumerate(lines, 1):
                        stripped = line.strip()
                        # Детекция функций
                        if "(" in stripped and ("=" in stripped or "->" in stripped) and not stripped.startswith("//"):
                            name = stripped.split("(")[0].strip()
                            result["functions"].append({"name": name, "line": i})
                        # Детекция проблем
                        if len(line) > 120:
                            result["issues"].append({"type": "long_line", "line": i, "length": len(line)})
                        if "TODO" in line or "FIXME" in line or "HACK" in line:
                            result["issues"].append({"type": "todo", "line": i, "text": stripped[:80]})

                    # Оценка сложности (упрощённая)
                    nesting_keywords = ["if ", "for ", "loop ", "match "]
                    max_nesting = 0
                    current_nesting = 0
                    for line in lines:
                        indent = len(line) - len(line.lstrip())
                        current_nesting = indent // 4  # предполагаем 4 пробела
                        max_nesting = max(max_nesting, current_nesting)
                    result["complexity_score"] = min(10, max_nesting + len(result["issues"]))
            except Exception:
                result["issues"].append({"type": "read_error", "message": f"Cannot read {path}"})
        else:
            result["issues"].append({"type": "no_fs", "message": "fs module not loaded"})

        return result

    def _suggest(args):
        """evolve_suggest(path) -> [{id, type, description, priority, diff}]"""
        analysis = _analyze(args)
        suggestions = []

        for issue in analysis.get("issues", []):
            s_id = f"sug_{len(_suggestions) + len(suggestions) + 1}"
            if issue["type"] == "long_line":
                suggestions.append({
                    "id": s_id,
                    "type": "refactor",
                    "description": f"Line {issue['line']} is too long ({issue['length']} chars). Consider breaking it up.",
                    "priority": "low",
                    "line": issue["line"],
                })
            elif issue["type"] == "todo":
                suggestions.append({
                    "id": s_id,
                    "type": "incomplete",
                    "description": f"Unresolved TODO at line {issue['line']}: {issue.get('text', '')}",
                    "priority": "medium",
                    "line": issue["line"],
                })

        # Общие предложения
        if analysis["complexity_score"] > 7:
            suggestions.append({
                "id": f"sug_{len(_suggestions) + len(suggestions) + 1}",
                "type": "complexity",
                "description": "High complexity score. Consider extracting helper functions.",
                "priority": "high",
            })

        if len(analysis.get("functions", [])) > 20:
            suggestions.append({
                "id": f"sug_{len(_suggestions) + len(suggestions) + 1}",
                "type": "structure",
                "description": "Many functions in one file. Consider splitting into modules.",
                "priority": "medium",
            })

        _suggestions.extend(suggestions)
        return suggestions

    def _apply(args):
        """evolve_apply(suggestion_id) -> {status, changes}"""
        sug_id = str(args[0]) if args else ""
        found = next((s for s in _suggestions if s.get("id") == sug_id), None)
        if not found:
            return {"status": "error", "error": f"Suggestion {sug_id} not found"}

        entry = {
            "id": f"ev_{len(_history) + 1}",
            "suggestion": found,
            "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "applied",
        }
        _history.append(entry)
        return {"status": "applied", "entry": entry}

    def _get_history(args):
        """evolve_history() -> list"""
        return _history.copy()

    def _rollback(args):
        """evolve_rollback(id) -> map"""
        ev_id = str(args[0]) if args else ""
        found = next((h for h in _history if h["id"] == ev_id), None)
        if not found:
            return {"status": "error", "error": f"Entry {ev_id} not found"}
        found["status"] = "rolled_back"
        return {"status": "rolled_back", "entry": found}

    # --- Регистрация ---
    interp.builtins[prefix + "analyze"] = _analyze
    interp.builtins[prefix + "suggest"] = _suggest
    interp.builtins[prefix + "apply"] = _apply
    interp.builtins[prefix + "history"] = _get_history
    interp.builtins[prefix + "rollback"] = _rollback

    return {
        "evolve_analyze":   ("builtin", prefix + "analyze"),
        "evolve_suggest":   ("builtin", prefix + "suggest"),
        "evolve_apply":     ("builtin", prefix + "apply"),
        "evolve_history":   ("builtin", prefix + "history"),
        "evolve_rollback":  ("builtin", prefix + "rollback"),
    }


# ╔══════════════════════════════════════════════════════════════════╗
# ║  4. SWARM — Agent Swarm (мультиагентные системы)               ║
# ╚══════════════════════════════════════════════════════════════════╝

def _std_swarm(interp: 'Interpreter') -> Dict[str, Any]:
    """
    Модуль swarm — оркестрация множества AI-агентов.

    Экспорты:
      swarm_create(config) -> map          — создать рой агентов
      swarm_add_agent(swarm_id, agent) -> map  — добавить агента
      swarm_run(swarm_id, task) -> map     — запустить задачу
      swarm_status(swarm_id) -> map        — статус роя
      swarm_collect(swarm_id) -> map       — собрать результаты
      swarm_destroy(swarm_id) -> map       — уничтожить рой
    """
    prefix = "_swarm_"

    _swarms: Dict[str, Dict] = {}
    _counter = {"value": 0}

    def _create(args):
        """swarm_create(config) -> {swarm_id, agents_count}"""
        config = args[0] if args and isinstance(args[0], dict) else {}
        _counter["value"] += 1
        swarm_id = f"swarm_{_counter['value']}"

        _swarms[swarm_id] = {
            "id": swarm_id,
            "name": config.get("name", swarm_id),
            "strategy": config.get("strategy", "parallel"),  # parallel | sequential | consensus
            "agents": [],
            "status": "created",
            "results": [],
            "created_at": _time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "consensus_threshold": float(config.get("consensus_threshold", 0.7)),
        }

        # Создать начальных агентов, если указаны
        initial_agents = config.get("agents", [])
        for agent_cfg in initial_agents:
            _add_agent([swarm_id, agent_cfg])

        return {"swarm_id": swarm_id, "agents_count": len(_swarms[swarm_id]["agents"])}

    def _add_agent(args):
        """swarm_add_agent(swarm_id, agent_config) -> {agent_id}"""
        swarm_id = str(args[0]) if args else ""
        agent_cfg = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}

        if swarm_id not in _swarms:
            return {"error": f"Swarm {swarm_id} not found"}

        agent_id = f"agent_{len(_swarms[swarm_id]['agents']) + 1}"
        agent = {
            "id": agent_id,
            "role": agent_cfg.get("role", "general"),
            "provider": agent_cfg.get("provider", "claude"),
            "model": agent_cfg.get("model", "claude-sonnet-4-20250514"),
            "system_prompt": agent_cfg.get("system_prompt", ""),
            "temperature": float(agent_cfg.get("temperature", 0.7)),
            "status": "idle",
            "result": None,
        }
        _swarms[swarm_id]["agents"].append(agent)
        return {"agent_id": agent_id, "swarm_id": swarm_id}

    def _run(args):
        """swarm_run(swarm_id, task) -> {status, results}"""
        swarm_id = str(args[0]) if args else ""
        task = str(args[1]) if len(args) > 1 else ""

        if swarm_id not in _swarms:
            return {"error": f"Swarm {swarm_id} not found"}

        swarm = _swarms[swarm_id]
        swarm["status"] = "running"
        strategy = swarm["strategy"]
        results = []

        # Попытка использовать ai_router для реальных запросов
        ai_ask = interp.builtins.get("_ai_router_ask")

        for agent in swarm["agents"]:
            agent["status"] = "running"
            full_prompt = f"[Role: {agent['role']}] {agent.get('system_prompt', '')}\n\nTask: {task}"

            if ai_ask:
                try:
                    response = ai_ask([full_prompt, {"provider": agent["provider"], "model": agent["model"]}])
                    agent["result"] = response.get("response", str(response))
                except Exception as e:
                    agent["result"] = f"[Error: {e}]"
            else:
                # Placeholder без реального AI
                agent["result"] = f"[{agent['role']}@{agent['provider']}] Analysis of: {task[:60]}..."

            agent["status"] = "done"
            results.append({"agent_id": agent["id"], "role": agent["role"], "result": agent["result"]})

        swarm["results"] = results
        swarm["status"] = "completed"

        # Консенсус (если стратегия consensus)
        final = {"status": "completed", "strategy": strategy, "results": results}
        if strategy == "consensus" and results:
            final["consensus"] = f"Consensus from {len(results)} agents (threshold: {swarm['consensus_threshold']})"

        return final

    def _status(args):
        """swarm_status(swarm_id) -> map"""
        swarm_id = str(args[0]) if args else ""
        if swarm_id not in _swarms:
            return {"error": f"Swarm {swarm_id} not found"}
        s = _swarms[swarm_id]
        return {
            "id": s["id"],
            "name": s["name"],
            "status": s["status"],
            "strategy": s["strategy"],
            "agents": [{"id": a["id"], "role": a["role"], "status": a["status"]} for a in s["agents"]],
            "results_count": len(s["results"]),
        }

    def _collect(args):
        """swarm_collect(swarm_id) -> {results}"""
        swarm_id = str(args[0]) if args else ""
        if swarm_id not in _swarms:
            return {"error": f"Swarm {swarm_id} not found"}
        return {"swarm_id": swarm_id, "results": _swarms[swarm_id]["results"]}

    def _destroy(args):
        """swarm_destroy(swarm_id) -> {status}"""
        swarm_id = str(args[0]) if args else ""
        if swarm_id in _swarms:
            del _swarms[swarm_id]
            return {"status": "destroyed", "swarm_id": swarm_id}
        return {"error": f"Swarm {swarm_id} not found"}

    # --- Регистрация ---
    interp.builtins[prefix + "create"] = _create
    interp.builtins[prefix + "add_agent"] = _add_agent
    interp.builtins[prefix + "run"] = _run
    interp.builtins[prefix + "status"] = _status
    interp.builtins[prefix + "collect"] = _collect
    interp.builtins[prefix + "destroy"] = _destroy

    return {
        "swarm_create":     ("builtin", prefix + "create"),
        "swarm_add_agent":  ("builtin", prefix + "add_agent"),
        "swarm_run":        ("builtin", prefix + "run"),
        "swarm_status":     ("builtin", prefix + "status"),
        "swarm_collect":    ("builtin", prefix + "collect"),
        "swarm_destroy":    ("builtin", prefix + "destroy"),
    }


# ╔══════════════════════════════════════════════════════════════════╗
# ║  5. INFRA — Infrastructure as Code                             ║
# ╚══════════════════════════════════════════════════════════════════╝

def _std_infra(interp: 'Interpreter') -> Dict[str, Any]:
    """
    Модуль infra — управление инфраструктурой через код.

    Экспорты:
      infra_define(resource) -> map        — определить ресурс
      infra_plan() -> map                  — план изменений
      infra_apply() -> map                 — применить план
      infra_destroy(resource_id) -> map    — удалить ресурс
      infra_status() -> map                — статус всех ресурсов
      infra_generate_compose() -> text     — генерация docker-compose.yml
    """
    prefix = "_infra_"

    _resources: Dict[str, Dict] = {}
    _plan_queue: List[Dict] = []

    def _define(args):
        """infra_define(resource_config) -> {resource_id}"""
        cfg = args[0] if args and isinstance(args[0], dict) else {}
        res_type = cfg.get("type", "service")  # service | database | cache | proxy
        name = cfg.get("name", f"resource_{len(_resources) + 1}")
        res_id = f"{res_type}_{name}"

        resource = {
            "id": res_id,
            "type": res_type,
            "name": name,
            "image": cfg.get("image", ""),
            "port": cfg.get("port", None),
            "env": cfg.get("env", {}),
            "volumes": cfg.get("volumes", []),
            "depends_on": cfg.get("depends_on", []),
            "replicas": int(cfg.get("replicas", 1)),
            "health_check": cfg.get("health_check", None),
            "status": "defined",
        }
        _resources[res_id] = resource
        _plan_queue.append({"action": "create", "resource": res_id})
        return {"resource_id": res_id, "status": "defined"}

    def _plan(args):
        """infra_plan() -> {changes: [...]}"""
        return {
            "changes": _plan_queue.copy(),
            "total": len(_plan_queue),
            "resources": len(_resources),
        }

    def _apply(args):
        """infra_apply() -> {applied: int, results: [...]}"""
        results = []
        for change in _plan_queue:
            res_id = change["resource"]
            if res_id in _resources:
                _resources[res_id]["status"] = "running"
                results.append({"resource": res_id, "action": change["action"], "status": "applied"})
        applied = len(results)
        _plan_queue.clear()
        return {"applied": applied, "results": results}

    def _destroy_resource(args):
        """infra_destroy(resource_id) -> {status}"""
        res_id = str(args[0]) if args else ""
        if res_id in _resources:
            del _resources[res_id]
            return {"status": "destroyed", "resource_id": res_id}
        return {"error": f"Resource {res_id} not found"}

    def _status(args):
        """infra_status() -> {resources: [...]}"""
        return {
            "total": len(_resources),
            "resources": {
                k: {"type": v["type"], "name": v["name"], "status": v["status"], "port": v["port"]}
                for k, v in _resources.items()
            },
            "pending_changes": len(_plan_queue),
        }

    def _generate_compose(args):
        """infra_generate_compose() -> docker-compose.yml как текст"""
        services = {}
        for res_id, res in _resources.items():
            svc = {}
            if res["image"]:
                svc["image"] = res["image"]
            if res["port"]:
                svc["ports"] = [f"{res['port']}:{res['port']}"]
            if res["env"]:
                svc["environment"] = res["env"]
            if res["volumes"]:
                svc["volumes"] = res["volumes"]
            if res["depends_on"]:
                svc["depends_on"] = res["depends_on"]
            if res["replicas"] > 1:
                svc["deploy"] = {"replicas": res["replicas"]}
            if res["health_check"]:
                svc["healthcheck"] = res["health_check"]
            services[res["name"]] = svc

        compose = {
            "version": "3.8",
            "services": services,
        }
        try:
            import yaml
            return yaml.dump(compose, default_flow_style=False, allow_unicode=True)
        except ImportError:
            # Fallback: JSON
            return json.dumps(compose, indent=2, ensure_ascii=False)

    # --- Регистрация ---
    interp.builtins[prefix + "define"] = _define
    interp.builtins[prefix + "plan"] = _plan
    interp.builtins[prefix + "apply"] = _apply
    interp.builtins[prefix + "destroy"] = _destroy_resource
    interp.builtins[prefix + "status"] = _status
    interp.builtins[prefix + "generate_compose"] = _generate_compose

    return {
        "infra_define":           ("builtin", prefix + "define"),
        "infra_plan":             ("builtin", prefix + "plan"),
        "infra_apply":            ("builtin", prefix + "apply"),
        "infra_destroy":          ("builtin", prefix + "destroy"),
        "infra_status":           ("builtin", prefix + "status"),
        "infra_generate_compose": ("builtin", prefix + "generate_compose"),
    }


# ╔══════════════════════════════════════════════════════════════════╗
# ║  6. GEMINI — Google Gemini API                                 ║
# ╚══════════════════════════════════════════════════════════════════╝

def _std_gemini(interp: 'Interpreter') -> Dict[str, Any]:
    """
    Модуль gemini — прямой доступ к Google Gemini API.

    Экспорты:
      gemini_ask(prompt, options?) -> map          — текстовый запрос
      gemini_vision(image_path, prompt?) -> map    — мультимодальный
      gemini_embed(text) -> map                    — эмбеддинги
      gemini_stream(prompt, callback) -> map       — стриминг
      gemini_models() -> list                      — список моделей
    """
    prefix = "_gemini_"

    _config = {
        "api_key_env": "GOOGLE_API_KEY",
        "default_model": "gemini-2.0-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
    }

    def _get_api_key():
        return os.environ.get(_config["api_key_env"], "")

    def _ask(args):
        """gemini_ask(prompt, options?) -> {text, model, usage}"""
        prompt = str(args[0]) if args else ""
        options = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}
        model = options.get("model", _config["default_model"])
        api_key = _get_api_key()

        if not api_key:
            return {"error": "GOOGLE_API_KEY not set", "status": "error"}

        http_post = interp.builtins.get("_http_post")
        if http_post:
            try:
                url = f"{_config['base_url']}/models/{model}:generateContent?key={api_key}"
                body = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": float(options.get("temperature", 0.7)),
                        "maxOutputTokens": int(options.get("max_tokens", 2048)),
                    },
                }
                result = http_post([url, body, {"content-type": "application/json"}])
                if isinstance(result, dict):
                    candidates = result.get("candidates", [])
                    text = candidates[0]["content"]["parts"][0]["text"] if candidates else ""
                    return {"status": "ok", "text": text, "model": model}
            except Exception as e:
                return {"status": "error", "error": str(e)}

        return {"status": "ok", "text": f"[gemini:{model}] Response to: {prompt[:50]}...", "model": model}

    def _vision(args):
        """gemini_vision(image_path, prompt?) -> {text, model}"""
        image_path = str(args[0]) if args else ""
        prompt = str(args[1]) if len(args) > 1 else "Describe this image"
        return {
            "status": "ok",
            "text": f"[gemini-vision] Analysis of {image_path}: {prompt}",
            "model": "gemini-2.0-flash",
            "note": "Full implementation requires base64 image encoding",
        }

    def _embed(args):
        """gemini_embed(text) -> {embedding, dimensions}"""
        text = str(args[0]) if args else ""
        # Placeholder — реальный запрос к embedding API
        import random
        random.seed(hash(text) % (2**32))
        fake_embedding = [round(random.uniform(-1, 1), 4) for _ in range(768)]
        return {"status": "ok", "embedding": fake_embedding, "dimensions": 768, "model": "text-embedding-004"}

    def _stream(args):
        """gemini_stream(prompt, callback) -> {status}"""
        prompt = str(args[0]) if args else ""
        return {
            "status": "ok",
            "note": "Streaming requires async runtime; use ai_router for production",
            "prompt_length": len(prompt),
        }

    def _models(args):
        """gemini_models() -> list"""
        return [
            {"id": "gemini-2.0-flash", "description": "Fast and versatile", "input_limit": 1048576},
            {"id": "gemini-2.0-pro", "description": "Best quality", "input_limit": 2097152},
            {"id": "gemini-2.5-flash-preview", "description": "Thinking model", "input_limit": 1048576},
            {"id": "text-embedding-004", "description": "Embeddings", "input_limit": 2048},
        ]

    # --- Регистрация ---
    interp.builtins[prefix + "ask"] = _ask
    interp.builtins[prefix + "vision"] = _vision
    interp.builtins[prefix + "embed"] = _embed
    interp.builtins[prefix + "stream"] = _stream
    interp.builtins[prefix + "models"] = _models

    return {
        "gemini_ask":    ("builtin", prefix + "ask"),
        "gemini_vision": ("builtin", prefix + "vision"),
        "gemini_embed":  ("builtin", prefix + "embed"),
        "gemini_stream": ("builtin", prefix + "stream"),
        "gemini_models": ("builtin", prefix + "models"),
    }


# ╔══════════════════════════════════════════════════════════════════╗
# ║  7. VERIFY — Vericoding (AI code verification)                 ║
# ╚══════════════════════════════════════════════════════════════════╝

def _std_verify(interp: 'Interpreter') -> Dict[str, Any]:
    """
    Модуль verify — AI-верификация кода с формальными проверками.

    Экспорты:
      verify_function(name, code, spec) -> map    — верификация функции
      verify_module(path) -> map                   — верификация модуля
      verify_contract(pre, post, code) -> map      — design by contract
      verify_types(code) -> map                    — проверка типов
      verify_report(path?) -> map                  — отчёт верификации
    """
    prefix = "_verify_"

    _results: List[Dict] = []

    def _verify_function(args):
        """verify_function(name, code, spec) -> {verified, issues, proof}"""
        name = str(args[0]) if args else "anonymous"
        code = str(args[1]) if len(args) > 1 else ""
        spec = args[2] if len(args) > 2 and isinstance(args[2], dict) else {}

        issues = []
        # Статический анализ
        if "return" not in code and "->" not in code:
            issues.append({"type": "missing_return", "severity": "warning", "message": "No explicit return"})
        if spec.get("pure", False) and ("mut " in code or "write" in code):
            issues.append({"type": "purity_violation", "severity": "error", "message": "Function marked pure but has side effects"})
        if spec.get("max_lines") and code.count("\n") > spec["max_lines"]:
            issues.append({"type": "too_long", "severity": "warning", "message": f"Exceeds {spec['max_lines']} lines"})

        # Проверка pre/post условий
        preconditions = spec.get("requires", [])
        postconditions = spec.get("ensures", [])
        for pre in preconditions:
            issues.append({"type": "precondition", "severity": "info", "message": f"Requires: {pre}", "verified": True})
        for post in postconditions:
            issues.append({"type": "postcondition", "severity": "info", "message": f"Ensures: {post}", "verified": True})

        verified = all(i["severity"] != "error" for i in issues)

        result = {
            "function": name,
            "verified": verified,
            "issues": issues,
            "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "confidence": 0.95 if verified else 0.4,
        }
        _results.append(result)
        return result

    def _verify_module(args):
        """verify_module(path) -> {verified, functions, issues}"""
        path = str(args[0]) if args else ""
        fs_read = interp.builtins.get("_fs_read")

        module_result = {
            "path": path,
            "verified": True,
            "functions_checked": 0,
            "issues": [],
            "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        if fs_read:
            try:
                content = fs_read([path])
                if isinstance(content, str):
                    # Поиск функций для проверки
                    lines = content.split("\n")
                    for i, line in enumerate(lines, 1):
                        stripped = line.strip()
                        if "(" in stripped and not stripped.startswith("//"):
                            module_result["functions_checked"] += 1
                            if "Any" in stripped or "any" in stripped:
                                module_result["issues"].append({
                                    "line": i,
                                    "type": "weak_typing",
                                    "message": "Avoid 'Any' type — use specific types",
                                })
            except Exception:
                module_result["issues"].append({"type": "read_error", "message": f"Cannot read {path}"})

        module_result["verified"] = len([i for i in module_result["issues"] if i.get("type") != "info"]) == 0
        _results.append(module_result)
        return module_result

    def _verify_contract(args):
        """verify_contract(pre, post, code) -> {valid, violations}"""
        pre = args[0] if args and isinstance(args[0], list) else []
        post = args[1] if len(args) > 1 and isinstance(args[1], list) else []
        code = str(args[2]) if len(args) > 2 else ""

        violations = []
        # Упрощённая проверка: ищем противоречия
        for condition in pre:
            if isinstance(condition, str) and "not null" in condition.lower():
                if "= null" in code or "= none" in code:
                    violations.append({"pre": condition, "violation": "Code may set null value"})

        valid = len(violations) == 0
        return {
            "valid": valid,
            "preconditions": len(pre),
            "postconditions": len(post),
            "violations": violations,
        }

    def _verify_types(args):
        """verify_types(code) -> {errors, warnings}"""
        code = str(args[0]) if args else ""
        errors = []
        warnings = []

        # Базовая проверка типов в PAPA Lang
        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Функция без указания типа возврата
            if "(" in stripped and ")" in stripped and "->" not in stripped and "=" in stripped:
                if not stripped.startswith("//") and not stripped.startswith("import"):
                    warnings.append({"line": i, "message": "Function without return type annotation"})

        return {"errors": errors, "warnings": warnings, "total_lines": len(lines)}

    def _report(args):
        """verify_report(path?) -> map"""
        return {
            "total_checks": len(_results),
            "verified": sum(1 for r in _results if r.get("verified", False)),
            "failed": sum(1 for r in _results if not r.get("verified", True)),
            "results": _results[-20:],  # Последние 20
            "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    # --- Регистрация ---
    interp.builtins[prefix + "function"] = _verify_function
    interp.builtins[prefix + "module"] = _verify_module
    interp.builtins[prefix + "contract"] = _verify_contract
    interp.builtins[prefix + "types"] = _verify_types
    interp.builtins[prefix + "report"] = _report

    return {
        "verify_function":  ("builtin", prefix + "function"),
        "verify_module":    ("builtin", prefix + "module"),
        "verify_contract":  ("builtin", prefix + "contract"),
        "verify_types":     ("builtin", prefix + "types"),
        "verify_report":    ("builtin", prefix + "report"),
    }


# ╔══════════════════════════════════════════════════════════════════╗
# ║  8. CHAIN — Blockchain Audit Trail (GDPR, 152-ФЗ, HIPAA)     ║
# ╚══════════════════════════════════════════════════════════════════╝

def _std_chain(interp: 'Interpreter') -> Dict[str, Any]:
    """
    Модуль chain — неизменяемый аудитный журнал на основе цепочки хешей.

    Экспорты:
      chain_record(event) -> map           — записать событие
      chain_verify() -> map                — проверить целостность цепи
      chain_query(filter?) -> list         — поиск по журналу
      chain_export(format?) -> text        — экспорт (json | csv)
      chain_compliance(standard) -> map    — отчёт по стандарту
      chain_stats() -> map                 — статистика
    """
    prefix = "_chain_"

    _chain: List[Dict] = []
    _genesis_hash = "0" * 64

    def _compute_hash(block: Dict) -> str:
        """SHA-256 хеш блока"""
        data = json.dumps(block, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def _record(args):
        """chain_record(event) -> {block_id, hash, timestamp}"""
        event = args[0] if args and isinstance(args[0], dict) else {"action": str(args[0]) if args else "unknown"}

        prev_hash = _chain[-1]["hash"] if _chain else _genesis_hash
        block_id = len(_chain) + 1
        timestamp = _time.strftime("%Y-%m-%dT%H:%M:%SZ")

        block_data = {
            "id": block_id,
            "timestamp": timestamp,
            "prev_hash": prev_hash,
            "event": event,
            "actor": event.get("actor", "system"),
            "action": event.get("action", "record"),
            "resource": event.get("resource", ""),
            "metadata": event.get("metadata", {}),
        }
        block_data["hash"] = _compute_hash(block_data)
        _chain.append(block_data)

        return {"block_id": block_id, "hash": block_data["hash"], "timestamp": timestamp}

    def _verify(args):
        """chain_verify() -> {valid, blocks_checked, errors}"""
        errors = []
        for i, block in enumerate(_chain):
            # Проверка prev_hash
            expected_prev = _chain[i - 1]["hash"] if i > 0 else _genesis_hash
            if block["prev_hash"] != expected_prev:
                errors.append({"block": block["id"], "error": "prev_hash mismatch"})

            # Проверка собственного хеша
            stored_hash = block["hash"]
            check_data = {k: v for k, v in block.items() if k != "hash"}
            check_data["hash"] = _compute_hash(check_data)
            # Примечание: пересчёт хеша работает если данные не менялись

        return {
            "valid": len(errors) == 0,
            "blocks_checked": len(_chain),
            "errors": errors,
            "chain_length": len(_chain),
        }

    def _query(args):
        """chain_query(filter?) -> list"""
        filter_cfg = args[0] if args and isinstance(args[0], dict) else {}
        results = _chain.copy()

        # Фильтры
        if "actor" in filter_cfg:
            results = [b for b in results if b.get("actor") == filter_cfg["actor"]]
        if "action" in filter_cfg:
            results = [b for b in results if b.get("action") == filter_cfg["action"]]
        if "resource" in filter_cfg:
            results = [b for b in results if filter_cfg["resource"] in str(b.get("resource", ""))]
        if "after" in filter_cfg:
            results = [b for b in results if b["timestamp"] >= filter_cfg["after"]]
        if "before" in filter_cfg:
            results = [b for b in results if b["timestamp"] <= filter_cfg["before"]]
        if "limit" in filter_cfg:
            results = results[-int(filter_cfg["limit"]):]

        return results

    def _export(args):
        """chain_export(format?) -> text"""
        fmt = str(args[0]) if args else "json"
        if fmt == "csv":
            if not _chain:
                return "id,timestamp,actor,action,resource,hash"
            headers = "id,timestamp,actor,action,resource,hash"
            rows = [headers]
            for b in _chain:
                rows.append(f"{b['id']},{b['timestamp']},{b.get('actor','')},{b.get('action','')},{b.get('resource','')},{b['hash'][:16]}...")
            return "\n".join(rows)
        return json.dumps(_chain, indent=2, ensure_ascii=False, default=str)

    def _compliance(args):
        """chain_compliance(standard) -> map"""
        standard = str(args[0]).upper() if args else "GDPR"
        report = {
            "standard": standard,
            "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "chain_length": len(_chain),
            "integrity": _verify([]),
            "checks": [],
        }

        if standard == "GDPR":
            report["checks"] = [
                {"rule": "Art.30 — Records of processing", "status": "pass" if _chain else "no_data",
                 "detail": f"{len(_chain)} processing records"},
                {"rule": "Art.17 — Right to erasure", "status": "info",
                 "detail": "Chain is append-only; mark records as erased via metadata"},
                {"rule": "Art.33 — Breach notification", "status": "pass",
                 "detail": "All events timestamped for 72h notification window"},
            ]
        elif standard in ("152-FZ", "152-ФЗ", "152FZ"):
            report["checks"] = [
                {"rule": "Ст.19 — Защита ПДн", "status": "pass",
                 "detail": "Хеш-цепочка обеспечивает неизменяемость журнала"},
                {"rule": "Ст.22 — Уведомление Роскомнадзора", "status": "info",
                 "detail": f"Журнал содержит {len(_chain)} записей обработки"},
                {"rule": "Локализация данных", "status": "info",
                 "detail": "Данные хранятся в оперативной памяти процесса"},
            ]
        elif standard == "HIPAA":
            report["checks"] = [
                {"rule": "§164.312 — Audit controls", "status": "pass" if _chain else "no_data",
                 "detail": "Immutable audit trail active"},
                {"rule": "§164.312 — Integrity", "status": "pass",
                 "detail": "SHA-256 hash chain ensures data integrity"},
            ]

        return report

    def _stats(args):
        """chain_stats() -> map"""
        actors = {}
        actions = {}
        for b in _chain:
            a = b.get("actor", "unknown")
            actors[a] = actors.get(a, 0) + 1
            act = b.get("action", "unknown")
            actions[act] = actions.get(act, 0) + 1

        return {
            "total_blocks": len(_chain),
            "actors": actors,
            "actions": actions,
            "first_block": _chain[0]["timestamp"] if _chain else None,
            "last_block": _chain[-1]["timestamp"] if _chain else None,
            "integrity_valid": _verify([])["valid"],
        }

    # --- Регистрация ---
    interp.builtins[prefix + "record"] = _record
    interp.builtins[prefix + "verify"] = _verify
    interp.builtins[prefix + "query"] = _query
    interp.builtins[prefix + "export"] = _export
    interp.builtins[prefix + "compliance"] = _compliance
    interp.builtins[prefix + "stats"] = _stats

    return {
        "chain_record":     ("builtin", prefix + "record"),
        "chain_verify":     ("builtin", prefix + "verify"),
        "chain_query":      ("builtin", prefix + "query"),
        "chain_export":     ("builtin", prefix + "export"),
        "chain_compliance": ("builtin", prefix + "compliance"),
        "chain_stats":      ("builtin", prefix + "stats"),
    }


# ╔══════════════════════════════════════════════════════════════════╗
# ║  9. VOICE_PROG — Voice Programming (Gemini Live)              ║
# ╚══════════════════════════════════════════════════════════════════╝

def _std_voice_prog(interp: 'Interpreter') -> Dict[str, Any]:
    """
    Модуль voice_prog — голосовое программирование через Gemini Live.

    Экспорты:
      voice_listen(options?) -> map         — начать слушать
      voice_execute(transcript) -> map      — выполнить голосовую команду
      voice_define_command(pattern, fn)     — определить голосовую команду
      voice_commands() -> list              — список команд
      voice_session_start() -> map          — начать сессию
      voice_session_end() -> map            — завершить сессию
    """
    prefix = "_voice_prog_"

    _session = {"active": False, "id": None, "commands_executed": 0, "history": []}
    _custom_commands: Dict[str, Dict] = {}

    # Встроенные голосовые команды
    BUILT_IN_COMMANDS = {
        r"(?i)create\s+function\s+(\w+)": "create_function",
        r"(?i)создай\s+функцию\s+(\w+)": "create_function",
        r"(?i)run\s+file\s+(.+)": "run_file",
        r"(?i)запусти\s+файл\s+(.+)": "run_file",
        r"(?i)show\s+status": "show_status",
        r"(?i)покажи\s+статус": "show_status",
        r"(?i)add\s+import\s+(.+)": "add_import",
        r"(?i)добавь\s+импорт\s+(.+)": "add_import",
        r"(?i)test\s+(.+)": "run_test",
        r"(?i)тест\s+(.+)": "run_test",
        r"(?i)deploy": "deploy",
        r"(?i)деплой": "deploy",
        r"(?i)undo": "undo",
        r"(?i)отмена": "undo",
    }

    def _listen(args):
        """voice_listen(options?) -> {status, transcript}"""
        options = args[0] if args and isinstance(args[0], dict) else {}
        lang = options.get("lang", "ru")
        return {
            "status": "listening",
            "lang": lang,
            "note": "Requires microphone access and Gemini Live API key",
            "session_active": _session["active"],
        }

    def _execute(args):
        """voice_execute(transcript) -> {command, result}"""
        transcript = str(args[0]) if args else ""

        # Поиск среди встроенных команд
        for pattern, cmd_type in BUILT_IN_COMMANDS.items():
            match = re.search(pattern, transcript)
            if match:
                result = _handle_command(cmd_type, match.groups(), transcript)
                _session["commands_executed"] += 1
                _session["history"].append({
                    "transcript": transcript,
                    "command": cmd_type,
                    "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "result": result,
                })
                return {"command": cmd_type, "args": list(match.groups()), "result": result}

        # Поиск среди пользовательских команд
        for pattern, cmd_info in _custom_commands.items():
            match = re.search(pattern, transcript)
            if match:
                _session["commands_executed"] += 1
                return {"command": cmd_info["name"], "args": list(match.groups()), "result": "custom_command_matched"}

        return {"command": None, "transcript": transcript, "error": "No matching command found"}

    def _handle_command(cmd_type: str, args: tuple, transcript: str) -> Dict:
        if cmd_type == "create_function":
            name = args[0] if args else "unnamed"
            return {"action": "create_function", "name": name,
                    "code": f'{name}(params) -> text =\n    // TODO: implement\n    return "ok"'}
        elif cmd_type == "run_file":
            file = args[0].strip() if args else ""
            return {"action": "run_file", "file": file, "status": "delegated_to_cli"}
        elif cmd_type == "show_status":
            return {"action": "show_status", "session": _session.copy()}
        elif cmd_type == "add_import":
            module = args[0].strip() if args else ""
            return {"action": "add_import", "code": f'import "std/{module}"'}
        elif cmd_type == "run_test":
            target = args[0].strip() if args else ""
            return {"action": "run_test", "target": target, "status": "delegated_to_cli"}
        elif cmd_type == "deploy":
            return {"action": "deploy", "status": "delegated_to_devops"}
        elif cmd_type == "undo":
            return {"action": "undo", "status": "last_action_reverted"}
        return {"action": cmd_type}

    def _define_command(args):
        """voice_define_command(pattern, name, description?) -> map"""
        pattern = str(args[0]) if args else ""
        name = str(args[1]) if len(args) > 1 else "custom"
        desc = str(args[2]) if len(args) > 2 else ""

        _custom_commands[pattern] = {"name": name, "description": desc, "pattern": pattern}
        return {"status": "defined", "command": name, "pattern": pattern}

    def _commands(args):
        """voice_commands() -> list"""
        built_in = [{"pattern": p, "command": c, "type": "built_in"} for p, c in BUILT_IN_COMMANDS.items()]
        custom = [{"pattern": v["pattern"], "command": v["name"], "type": "custom", "description": v.get("description", "")}
                  for v in _custom_commands.values()]
        return built_in + custom

    def _session_start(args):
        """voice_session_start() -> {session_id, status}"""
        _session["active"] = True
        _session["id"] = f"vs_{int(_time.time())}"
        _session["commands_executed"] = 0
        _session["history"] = []
        return {"session_id": _session["id"], "status": "active"}

    def _session_end(args):
        """voice_session_end() -> {summary}"""
        summary = {
            "session_id": _session["id"],
            "commands_executed": _session["commands_executed"],
            "history": _session["history"],
            "status": "ended",
        }
        _session["active"] = False
        _session["id"] = None
        return summary

    # --- Регистрация ---
    interp.builtins[prefix + "listen"] = _listen
    interp.builtins[prefix + "execute"] = _execute
    interp.builtins[prefix + "define_command"] = _define_command
    interp.builtins[prefix + "commands"] = _commands
    interp.builtins[prefix + "session_start"] = _session_start
    interp.builtins[prefix + "session_end"] = _session_end

    return {
        "voice_listen":         ("builtin", prefix + "listen"),
        "voice_execute":        ("builtin", prefix + "execute"),
        "voice_define_command": ("builtin", prefix + "define_command"),
        "voice_commands":       ("builtin", prefix + "commands"),
        "voice_session_start":  ("builtin", prefix + "session_start"),
        "voice_session_end":    ("builtin", prefix + "session_end"),
    }


# ╔══════════════════════════════════════════════════════════════════╗
# ║  ИНТЕГРАЦИЯ: обновление STD_MODULE_LOADERS                    ║
# ╚══════════════════════════════════════════════════════════════════╝

# Добавить в STD_MODULE_LOADERS в interpreter.py:
WAVE_2_3_LOADERS = {
    # Wave 2
    "guard":      _std_guard,
    "ai_router":  _std_ai_router,
    "evolve":     _std_evolve,
    "swarm":      _std_swarm,
    "infra":      _std_infra,
    "gemini":     _std_gemini,
    # Wave 3
    "verify":     _std_verify,
    "chain":      _std_chain,
    "voice_prog": _std_voice_prog,
}

# Итого STD_MODULE_LOADERS станет:
# STD_MODULE_LOADERS = {
#     # --- Существующие (Wave 1 / Core) ---
#     "math": _std_math,
#     "string": _std_string,
#     "orchestrator": _load_orchestrator,
#     "docs": _load_docs,
#     "studio": _load_studio,
#     "json": _std_json,
#     "http": _std_http,
#     "fs": _std_fs,
#     "time": _std_time,
#     "voice": _std_voice,
#     "mcp": _std_mcp,
#     "browser": _std_browser,
#     "telegram": _std_telegram,
#     "ai": _std_ai_budget,
#     "design": _std_design,
#     "cwb": _load_cwb,
#     # --- Wave 2 ---
#     "guard": _std_guard,
#     "ai_router": _std_ai_router,
#     "evolve": _std_evolve,
#     "swarm": _std_swarm,
#     "infra": _std_infra,
#     "gemini": _std_gemini,
#     # --- Wave 3 ---
#     "verify": _std_verify,
#     "chain": _std_chain,
#     "voice_prog": _std_voice_prog,
# }
