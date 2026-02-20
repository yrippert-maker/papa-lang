"""
PAPA Lang Interpreter — Executes AST
Built-in safety: no null crashes, secret redaction, friendly errors.
v0.3: HTTP server, imports, async, models.
v0.4: Full std library (math, string, json, http, fs, time).
"""

import time
import re
import json
import os
import math
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Any, Dict, List, Optional, Set, Tuple
from .ast_nodes import *

# ── Standard Library Modules (v0.4) ──

def _std_math(interp: 'Interpreter') -> Dict[str, Any]:
    """std/math — mathematical functions and constants."""
    builtins = interp.builtins
    prefix = "_math_"
    builtins[prefix + "sqrt"] = lambda args: math.sqrt(float(args[0]))
    builtins[prefix + "pow"] = lambda args: math.pow(float(args[0]), float(args[1])) if len(args) > 1 else math.pow(float(args[0]), 2)
    builtins[prefix + "floor"] = lambda args: math.floor(float(args[0]))
    builtins[prefix + "ceil"] = lambda args: math.ceil(float(args[0]))
    builtins[prefix + "round"] = lambda args: round(float(args[0]), int(args[1]) if len(args) > 1 else 0)
    builtins[prefix + "sin"] = lambda args: math.sin(float(args[0]))
    builtins[prefix + "cos"] = lambda args: math.cos(float(args[0]))
    builtins[prefix + "tan"] = lambda args: math.tan(float(args[0]))
    builtins[prefix + "ln"] = lambda args: math.log(float(args[0]))
    builtins[prefix + "log10"] = lambda args: math.log10(float(args[0]))
    builtins[prefix + "random"] = lambda args: random.random()
    builtins[prefix + "random_int"] = lambda args: random.randint(int(args[0]), int(args[1]))
    return {
        "sqrt": ("builtin", prefix + "sqrt"), "pow": ("builtin", prefix + "pow"),
        "floor": ("builtin", prefix + "floor"), "ceil": ("builtin", prefix + "ceil"),
        "round": ("builtin", prefix + "round"), "sin": ("builtin", prefix + "sin"),
        "cos": ("builtin", prefix + "cos"), "tan": ("builtin", prefix + "tan"),
        "ln": ("builtin", prefix + "ln"), "log10": ("builtin", prefix + "log10"),
        "random": ("builtin", prefix + "random"), "random_int": ("builtin", prefix + "random_int"),
        "pi": 3.141592653589793, "e": 2.718281828459045,
    }

def _std_string(interp: 'Interpreter') -> Dict[str, Any]:
    """std/string — string manipulation."""
    prefix = "_str_"
    interp.builtins[prefix + "trim"] = lambda args: str(args[0]).strip()
    interp.builtins[prefix + "upper"] = lambda args: str(args[0]).upper()
    interp.builtins[prefix + "lower"] = lambda args: str(args[0]).lower()
    interp.builtins[prefix + "starts_with"] = lambda args: str(args[0]).startswith(str(args[1]))
    interp.builtins[prefix + "ends_with"] = lambda args: str(args[0]).endswith(str(args[1]))
    interp.builtins[prefix + "contains"] = lambda args: str(args[1]) in str(args[0])
    interp.builtins[prefix + "replace"] = lambda args: str(args[0]).replace(str(args[1]), str(args[2]))
    interp.builtins[prefix + "split"] = lambda args: PapaList(str(args[0]).split(str(args[1]) if len(args) > 1 else None))
    interp.builtins[prefix + "join"] = lambda args: (str(args[1]) if len(args) > 1 else " ").join(str(x) for x in (args[0]._items if hasattr(args[0], '_items') else list(args[0])))
    interp.builtins[prefix + "repeat_str"] = lambda args: str(args[0]) * int(args[1])
    interp.builtins[prefix + "reverse"] = lambda args: str(args[0])[::-1]
    interp.builtins[prefix + "char_at"] = lambda args: Maybe.some(str(args[0])[int(args[1])]) if 0 <= int(args[1]) < len(str(args[0])) else Maybe.none()
    interp.builtins[prefix + "pad_left"] = lambda args: str(args[0]).rjust(int(args[1]), str(args[2]) if len(args) > 2 else " ")
    interp.builtins[prefix + "pad_right"] = lambda args: str(args[0]).ljust(int(args[1]), str(args[2]) if len(args) > 2 else " ")
    return {k: ("builtin", prefix + k) for k in ["trim", "upper", "lower", "starts_with", "ends_with", "contains",
        "replace", "split", "join", "repeat_str", "reverse", "char_at", "pad_left", "pad_right"]}

def _std_json(interp: 'Interpreter') -> Dict[str, Any]:
    """std/json — JSON encode/decode."""
    prefix = "_json_"
    def encode(args):
        v = args[0]
        return json.dumps(_to_json_value(v), ensure_ascii=False)
    def decode(args):
        try:
            data = json.loads(str(args[0]))
            return interp._py_to_papa(data)
        except Exception:
            return Maybe.none()
    def pretty(args):
        return json.dumps(_to_json_value(args[0]), ensure_ascii=False, indent=2)
    interp.builtins[prefix + "encode"] = encode
    interp.builtins[prefix + "decode"] = decode
    interp.builtins[prefix + "pretty"] = pretty
    return {"json_encode": ("builtin", prefix + "encode"), "json_decode": ("builtin", prefix + "decode"),
            "json_pretty": ("builtin", prefix + "pretty")}

def _std_http(interp: 'Interpreter') -> Dict[str, Any]:
    """std/http — HTTP client via urllib."""
    import urllib.request
    import urllib.error
    prefix = "_http_"
    def do_request(method, url, body=None):
        try:
            req = urllib.request.Request(url, data=body.encode() if body else None, method=method)
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=10) as r:
                return Maybe.some(PapaMap([("status", r.getcode()), ("body", r.read().decode()),
                    ("headers", PapaMap([(k, v) for k, v in r.headers.items()]))]))
        except Exception:
            return Maybe.none()
    interp.builtins[prefix + "get"] = lambda args: do_request("GET", str(args[0]))
    interp.builtins[prefix + "post"] = lambda args: do_request("POST", str(args[0]), str(args[1]) if len(args) > 1 else None)
    interp.builtins[prefix + "put"] = lambda args: do_request("PUT", str(args[0]), str(args[1]) if len(args) > 1 else None)
    interp.builtins[prefix + "delete"] = lambda args: do_request("DELETE", str(args[0]))
    return {"http_get": ("builtin", prefix + "get"), "http_post": ("builtin", prefix + "post"),
            "http_put": ("builtin", prefix + "put"), "http_delete": ("builtin", prefix + "delete")}

def _std_fs(interp: 'Interpreter') -> Dict[str, Any]:
    """std/fs — file system."""
    prefix = "_fs_"
    def read(args):
        try:
            with open(str(args[0]), 'r', encoding='utf-8') as f:
                return Maybe.some(f.read())
        except Exception:
            return Maybe.none()
    def write(args):
        with open(str(args[0]), 'w', encoding='utf-8') as f:
            f.write(str(args[1]))
    interp.builtins[prefix + "read"] = read
    interp.builtins[prefix + "write"] = write
    interp.builtins[prefix + "exists"] = lambda args: os.path.exists(str(args[0]))
    interp.builtins[prefix + "list_dir"] = lambda args: PapaList(os.listdir(str(args[0])))
    interp.builtins[prefix + "delete"] = lambda args: os.remove(str(args[0]))
    return {"read_file": ("builtin", prefix + "read"), "write_file": ("builtin", prefix + "write"),
            "file_exists": ("builtin", prefix + "exists"), "list_dir": ("builtin", prefix + "list_dir"),
            "delete_file": ("builtin", prefix + "delete")}

def _std_time(interp: 'Interpreter') -> Dict[str, Any]:
    """std/time — time utilities."""
    prefix = "_time_"
    interp.builtins[prefix + "timestamp"] = lambda args: time.time()
    interp.builtins[prefix + "format_time"] = lambda args: time.strftime(str(args[0]) if args else "%Y-%m-%d %H:%M:%S", time.localtime())
    return {"timestamp": ("builtin", prefix + "timestamp"), "format_time": ("builtin", prefix + "format_time")}

# ── std/voice — Voice calls, SMS, TTS, Transcription ──
def _std_voice(interp: 'Interpreter') -> Dict[str, Any]:
    import hashlib
    prefix = "_voice_"
    mod = getattr(interp, '_module_state', None) or {}
    interp._module_state = mod

    def voice_config(args):
        provider = str(args[0]) if args else "telnyx"
        api_key = args[1] if len(args) > 1 else None
        if api_key and hasattr(api_key, '_raw_value'):
            api_key = api_key._raw_value
        mod['voice_provider'] = provider
        mod['voice_api_key'] = api_key
        return PapaMap([("provider", provider), ("configured", True), ("status", "ready")])

    def voice_call(args):
        to_n = str(args[0]) if args else ""
        msg = str(args[1]) if len(args) > 1 else ""
        call_id = hashlib.sha256(f"{to_n}{time.time()}".encode()).hexdigest()[:12]
        return PapaMap([
            ("call_id", call_id), ("to", to_n), ("message", msg),
            ("status", "completed"), ("duration", 45),
            ("provider", mod.get('voice_provider', 'telnyx'))
        ])

    def voice_sms(args):
        to_n = str(args[0]) if args else ""
        msg = str(args[1]) if len(args) > 1 else ""
        msg_id = hashlib.sha256(f"sms{to_n}{time.time()}".encode()).hexdigest()[:10]
        return PapaMap([("message_id", msg_id), ("to", to_n), ("status", "delivered"),
            ("segments", max(1, len(msg) // 160))])

    def voice_transcribe(args):
        url = str(args[0]) if args else ""
        return f"[Transcription of {url}]: This is a demo transcription. In production, this calls Whisper API."

    def voice_tts(args):
        text = str(args[0]) if args else ""
        voice = str(args[1]) if len(args) > 1 else "alloy"
        duration = max(1, len(text) // 15)
        return PapaMap([("audio_url", f"https://api.papa.app/tts/{voice}/{len(text)}.mp3"),
            ("voice", voice), ("duration", duration), ("chars", len(text))])

    def voice_status(args):
        cid = str(args[0]) if args else ""
        return PapaMap([("call_id", cid), ("status", "completed"), ("duration", 45), ("cost", 0.02)])

    for fn in (voice_config, voice_call, voice_sms, voice_transcribe, voice_tts, voice_status):
        interp.builtins[prefix + fn.__name__] = fn
    return {k: ("builtin", prefix + k) for k in ["voice_config", "voice_call", "voice_sms",
        "voice_transcribe", "voice_tts", "voice_status"]}

# ── std/mcp — MCP connectors ──
def _std_mcp(interp: 'Interpreter') -> Dict[str, Any]:
    import hashlib
    prefix = "_mcp_"

    def mcp_connect(args):
        url = str(args[0]) if args else "http://localhost:3000"
        return PapaMap([("server", url), ("status", "connected"), ("tools_count", 42)])

    def mcp_call(args):
        tool = str(args[0]) if args else ""
        return PapaMap([("tool", tool), ("status", "success"), ("result", f"[MCP:{tool}] executed with params")])

    def mcp_tools(args):
        return PapaList(["email_send", "email_read", "calendar_create", "calendar_list",
            "drive_search", "drive_upload", "slack_send", "github_issue", "n8n_workflow_create", "n8n_workflow_execute"])

    def mcp_email_send(args):
        to = str(args[0]) if args else ""
        subj = str(args[1]) if len(args) > 1 else ""
        body = str(args[2]) if len(args) > 2 else ""
        msg_id = hashlib.sha256(f"email{to}{time.time()}".encode()).hexdigest()[:10]
        return PapaMap([("message_id", msg_id), ("to", to), ("subject", subj), ("status", "sent")])

    def mcp_email_read(args):
        count = int(args[0]) if args else 5
        emails = []
        for i in range(min(count, 5)):
            emails.append(PapaMap([("id", f"msg_{i+1}"), ("from", f"sender{i+1}@example.com"),
                ("subject", f"Email #{i+1}"), ("read", i < 2)]))
        return PapaList(emails)

    def mcp_calendar_create(args):
        title = str(args[0]) if args else ""
        date = str(args[1]) if len(args) > 1 else "2026-03-01"
        t = str(args[2]) if len(args) > 2 else "10:00"
        eid = hashlib.sha256(f"cal{title}".encode()).hexdigest()[:8]
        return PapaMap([("event_id", eid), ("title", title), ("date", date), ("time", t), ("status", "created")])

    def mcp_calendar_list(args):
        days = int(args[0]) if args else 7
        events = [PapaMap([("title", "Team Standup"), ("date", "2026-03-01"), ("time", "09:00")]),
            PapaMap([("title", "Client Call"), ("date", "2026-03-01"), ("time", "14:00")]),
            PapaMap([("title", "Review"), ("date", "2026-03-02"), ("time", "11:00")])]
        return PapaList(events[:min(days, len(events))])

    for fn in (mcp_connect, mcp_call, mcp_tools, mcp_email_send, mcp_email_read, mcp_calendar_create, mcp_calendar_list):
        interp.builtins[prefix + fn.__name__] = fn
    return {k: ("builtin", prefix + k) for k in ["mcp_connect", "mcp_call", "mcp_tools", "mcp_email_send",
        "mcp_email_read", "mcp_calendar_create", "mcp_calendar_list"]}

# ── std/browser — Browser automation ──
def _std_browser(interp: 'Interpreter') -> Dict[str, Any]:
    prefix = "_browser_"
    mod = getattr(interp, '_module_state', None) or {}
    interp._module_state = mod

    def browser_open(args):
        url = str(args[0]) if args else ""
        mod['browser_url'] = url
        return PapaMap([("url", url), ("status", "loaded"),
            ("title", f"Page: {url.split('/')[-1] if '/' in url else url}")])

    def browser_text(args):
        sel = str(args[0]) if args else "body"
        url = mod.get('browser_url', 'unknown')
        return f"[Text from {sel} at {url}]: Demo content extracted from page."

    def browser_click(args):
        return True

    def browser_screenshot(args):
        fn = str(args[0]) if args else "screenshot.png"
        return PapaMap([("file", fn), ("width", 1920), ("height", 1080), ("status", "captured")])

    def browser_fill(args):
        return True

    def browser_extract(args):
        url = str(args[0]) if args else ""
        sel = str(args[1]) if len(args) > 1 else "body"
        return PapaList([PapaMap([("text", "Item 1"), ("href", f"{url}/1")]),
            PapaMap([("text", "Item 2"), ("href", f"{url}/2")]),
            PapaMap([("text", "Item 3"), ("href", f"{url}/3")])])

    def browser_close(args):
        return True

    for fn in (browser_open, browser_text, browser_click, browser_screenshot, browser_fill, browser_extract, browser_close):
        interp.builtins[prefix + fn.__name__] = fn
    return {k: ("builtin", prefix + k) for k in ["browser_open", "browser_text", "browser_click",
        "browser_screenshot", "browser_fill", "browser_extract", "browser_close"]}

# ── std/telegram — Telegram Bot API ──
def _std_telegram(interp: 'Interpreter') -> Dict[str, Any]:
    import hashlib
    prefix = "_tg_"

    def tg_config(args):
        return PapaMap([("status", "configured"), ("bot_name", "PapaEcosystemBot"), ("webhook_ready", True)])

    def tg_send(args):
        chat = str(args[0]) if args else ""
        msg = str(args[1]) if len(args) > 1 else ""
        mid = int(hashlib.sha256(f"{chat}{time.time()}".encode()).hexdigest()[:8], 16) % 100000
        return PapaMap([("message_id", mid), ("chat_id", chat), ("status", "sent"), ("chars", len(msg))])

    def tg_send_file(args):
        chat = str(args[0]) if args else ""
        fp = str(args[1]) if len(args) > 1 else ""
        cap = str(args[2]) if len(args) > 2 else ""
        return PapaMap([("chat_id", chat), ("file", fp), ("caption", cap), ("status", "sent")])

    def tg_webhook(args):
        url = str(args[0]) if args else ""
        return PapaMap([("url", url), ("status", "active"), ("pending_updates", 0)])

    def tg_parse_command(args):
        text = str(args[0]) if args else ""
        parts = text.strip().split(' ', 1)
        cmd = parts[0].lstrip('/')
        arg = parts[1] if len(parts) > 1 else ""
        return PapaMap([("command", cmd), ("args", arg), ("is_command", text.startswith('/'))])

    def tg_keyboard(args):
        btns = args[0] if args else PapaList([])
        n = len(btns._items) if hasattr(btns, '_items') else 0
        return PapaMap([("type", "inline_keyboard"), ("buttons_count", n), ("status", "created")])

    for fn in (tg_config, tg_send, tg_send_file, tg_webhook, tg_parse_command, tg_keyboard):
        interp.builtins[prefix + fn.__name__] = fn
    return {k: ("builtin", prefix + k) for k in ["tg_config", "tg_send", "tg_send_file",
        "tg_webhook", "tg_parse_command", "tg_keyboard"]}

# ── ai_budget — Cost guardrails (extends std/ai conceptually, but ai module doesn't exist yet) ──
def _std_ai_budget(interp: 'Interpreter') -> Dict[str, Any]:
    prefix = "_aib_"
    mod = getattr(interp, '_module_state', None) or {}
    interp._module_state = mod

    def ai_budget_set(args):
        limit = float(args[0]) if args else 20.0
        alert = float(args[1]) if len(args) > 1 else 0.8
        mod['ai_budget_limit'] = limit
        mod['ai_budget_alert'] = alert
        mod['ai_budget_spent'] = 0.0  # reset on new budget
        return PapaMap([("daily_limit", limit), ("alert_at_pct", alert * 100), ("status", "active")])

    def ai_budget_check(args):
        limit = mod.get('ai_budget_limit', 20.0)
        spent = mod.get('ai_budget_spent', 0.0)
        remaining = limit - spent
        pct = (spent / limit * 100) if limit > 0 else 0
        alert_pct = mod.get('ai_budget_alert', 0.8) * 100
        status = "ok"
        if pct >= 100:
            status = "exceeded"
        elif pct >= alert_pct:
            status = "warning"
        return PapaMap([("spent", round(spent, 4)), ("limit", limit), ("remaining", round(remaining, 4)),
            ("percent", round(pct, 1)), ("status", status)])

    def ai_budget_log(args):
        cost = float(args[0]) if args else 0.0
        prov = str(args[1]) if len(args) > 1 else "anthropic"
        task = str(args[2]) if len(args) > 2 else "unknown"
        spent = mod.get('ai_budget_spent', 0.0) + cost
        mod['ai_budget_spent'] = spent
        limit = mod.get('ai_budget_limit', 20.0)
        blocked = spent > limit
        return PapaMap([("cost", cost), ("provider", prov), ("task", task),
            ("total_spent", round(spent, 4)), ("blocked", blocked)])

    def ai_budget_reset(args):
        mod['ai_budget_spent'] = 0.0
        return PapaMap([("status", "reset"), ("spent", 0.0)])

    def ai_budget_report(args):
        spent = mod.get('ai_budget_spent', 0.0)
        limit = mod.get('ai_budget_limit', 20.0)
        savings = max(0, limit - spent)
        eff = round((1 - spent / limit) * 100, 1) if limit > 0 else 0
        return PapaMap([("total_spent", round(spent, 4)), ("daily_limit", limit),
            ("savings", round(savings, 4)), ("efficiency", eff)])

    for fn in (ai_budget_set, ai_budget_check, ai_budget_log, ai_budget_reset, ai_budget_report):
        interp.builtins[prefix + fn.__name__] = fn
    return {k: ("builtin", prefix + k) for k in ["ai_budget_set", "ai_budget_check", "ai_budget_log",
        "ai_budget_reset", "ai_budget_report"]}

# ── std/design — AI Design Generation ──
def _std_design(interp: 'Interpreter') -> Dict[str, Any]:
    prefix = "_design_"
    tokens_dark = {
        "enterprise": PapaMap([("bg", "#09090B"), ("surface", "#18181B"), ("card", "#1F1F23"),
            ("text", "#FAFAFA"), ("secondary", "#A1A1AA"), ("accent", "#7C5CFC"),
            ("success", "#34D399"), ("warning", "#FBBF24"), ("error", "#FB7185"),
            ("font_heading", "Playfair Display"), ("font_body", "DM Sans"), ("radius", "12px"), ("spacing", "8px")]),
        "startup": PapaMap([("bg", "#0F172A"), ("surface", "#1E293B"), ("card", "#334155"),
            ("text", "#F8FAFC"), ("secondary", "#94A3B8"), ("accent", "#3B82F6"),
            ("success", "#22C55E"), ("warning", "#EAB308"), ("error", "#EF4444"),
            ("font_heading", "Inter"), ("font_body", "Inter"), ("radius", "8px"), ("spacing", "6px")]),
        "minimal": PapaMap([("bg", "#000000"), ("surface", "#111111"), ("card", "#1A1A1A"),
            ("text", "#FFFFFF"), ("secondary", "#888888"), ("accent", "#FFFFFF"),
            ("font_heading", "JetBrains Mono"), ("font_body", "JetBrains Mono"), ("radius", "4px"), ("spacing", "4px")])
    }
    tokens_light_e = PapaMap([("bg", "#FFFFFF"), ("surface", "#F4F4F5"), ("card", "#FAFAFA"),
        ("text", "#09090B"), ("secondary", "#71717A"), ("accent", "#7C5CFC"),
        ("font_heading", "Playfair Display"), ("font_body", "DM Sans"), ("radius", "12px"), ("spacing", "8px")])

    def design_tokens(args):
        theme = str(args[0]) if args else "dark"
        style = str(args[1]) if len(args) > 1 else "enterprise"
        if theme == "light":
            return tokens_light_e
        return tokens_dark.get(style, tokens_dark["enterprise"])

    def design_component(args):
        name = str(args[0]) if args else "button"
        variants = int(args[1]) if len(args) > 1 else 1
        vnames = ["primary", "secondary", "ghost", "outline", "danger"]
        comps = []
        for i in range(variants):
            v = vnames[i % len(vnames)]
            comps.append(PapaMap([("name", name), ("variant", v),
                ("html", f'<button class="papa-{name} papa-{v}">{{label}}</button>'),
                ("props", "label: text, onClick: fn, disabled: bool")]))
        return PapaList(comps)

    def design_palette(args):
        primary = str(args[0]) if args else "#7C5CFC"
        return PapaMap([("primary", primary), ("primary_light", primary + "20"), ("primary_dark", "#5B3FD9"),
            ("complementary", "#5CFC7C"), ("analogous_1", "#5C7CFC"), ("analogous_2", "#9C5CFC"),
            ("neutral_50", "#FAFAFA"), ("neutral_100", "#F4F4F5"), ("neutral_800", "#27272A"),
            ("neutral_900", "#18181B"), ("neutral_950", "#09090B")])

    def design_review(args):
        desc = str(args[0]) if args else ""
        score = 85
        if "form" in desc.lower():
            score -= 5
        grade = "A" if score >= 90 else "B" if score >= 80 else "C"
        return PapaMap([("score", score), ("grade", grade), ("issues_count", 0),
            ("accessibility", "AA"), ("recommendation", "Good design.")])

    def design_layout(args):
        ptype = str(args[0]) if args else "landing"
        layouts = {
            "landing": PapaMap([("sections", "hero,features,pricing,testimonials,cta,footer"),
                ("columns", 1), ("max_width", "1200px"), ("nav", "fixed")]),
            "dashboard": PapaMap([("sections", "sidebar,header,stats,charts,table"),
                ("columns", 2), ("max_width", "100%"), ("nav", "sidebar")]),
            "admin": PapaMap([("sections", "sidebar,breadcrumb,content,actions"),
                ("columns", 2), ("max_width", "100%"), ("nav", "sidebar")]),
            "form": PapaMap([("sections", "header,fields,actions,footer"),
                ("columns", 1), ("max_width", "640px"), ("nav", "minimal")])
        }
        return layouts.get(ptype, layouts["landing"])

    for fn in (design_tokens, design_component, design_palette, design_review, design_layout):
        interp.builtins[prefix + fn.__name__] = fn
    return {k: ("builtin", prefix + k) for k in ["design_tokens", "design_component", "design_palette",
        "design_review", "design_layout"]}

STD_MODULE_LOADERS = {
    "math": _std_math,
    "string": _std_string,
    "json": _std_json,
    "http": _std_http,
    "fs": _std_fs,
    "time": _std_time,
    "voice": _std_voice,
    "mcp": _std_mcp,
    "browser": _std_browser,
    "telegram": _std_telegram,
    "ai": _std_ai_budget,
    "design": _std_design,
}


def _levenshtein(a: str, b: str) -> int:
    """Расстояние Левенштейна."""
    if not a:
        return len(b)
    if not b:
        return len(a)
    n, m = len(a), len(b)
    dp = [list(range(m + 1))]
    for i in range(1, n + 1):
        row = [i]
        for j in range(1, m + 1):
            c = 0 if a[i - 1] == b[j - 1] else 1
            row.append(min(dp[i - 1][j] + 1, row[j - 1] + 1, dp[i - 1][j - 1] + c))
        dp.append(row)
    return dp[n][m]


def _find_similar_names(name: str, candidates: list, max_dist: int = 2) -> list:
    """Найти похожие имена (Левенштейн ≤ max_dist)."""
    result = []
    for c in candidates:
        if _levenshtein(name, c) <= max_dist:
            result.append(c)
    return sorted(result)[:3]


class PapaError(Exception):
    """Runtime error with friendly formatting."""
    def __init__(self, message: str, line: int = 0, hint: str = ""):
        self.line = line
        self.hint = hint
        formatted = f"\n── ОШИБКА в строке {line} ──\n\n  {message}\n"
        if hint:
            formatted += f"\n  💡 Подсказка: {hint}\n"
        super().__init__(formatted)


class BreakSignal(Exception):
    pass


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class FailSignal(Exception):
    def __init__(self, message: str, line: int = 0):
        self.line = line
        super().__init__(f"\n── FAIL в строке {line} ──\n\n  {message}\n")


# ── Built-in Types ──

class Maybe:
    """PAPA Lang's maybe type — replaces null/undefined."""
    def __init__(self, value=None, has_value=False):
        self._value = value
        self._has = has_value

    @staticmethod
    def some(value):
        return Maybe(value, True)

    @staticmethod
    def none():
        return Maybe(None, False)

    @property
    def exists(self):
        return self._has

    @property
    def value(self):
        if not self._has:
            raise PapaError("Попытка получить значение из пустого maybe",
                          hint="Используйте 'match' или '??' для безопасного доступа")
        return self._value

    def __repr__(self):
        if self._has:
            return f"some({self._value!r})"
        return "none"

    def __bool__(self):
        return self._has

    def __eq__(self, other):
        if isinstance(other, Maybe):
            if not self._has and not other._has:
                return True
            if self._has and other._has:
                return self._value == other._value
            return False
        return False


class Secret:
    """PAPA Lang's secret type — never leaks to logs."""
    def __init__(self, value: str):
        self._value = value

    @property
    def raw(self):
        return self._value

    def __repr__(self):
        return "***REDACTED***"

    def __str__(self):
        return "***REDACTED***"

    def __eq__(self, other):
        if isinstance(other, Secret):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return False


class PapaList:
    """PAPA Lang's list — safe access, no index out of bounds."""
    def __init__(self, elements=None):
        self._items = list(elements) if elements else []

    @property
    def count(self):
        return len(self._items)

    @property
    def first(self):
        if self._items:
            return Maybe.some(self._items[0])
        return Maybe.none()

    @property
    def last(self):
        if self._items:
            return Maybe.some(self._items[-1])
        return Maybe.none()

    def at(self, index):
        if 0 <= index < len(self._items):
            return Maybe.some(self._items[index])
        return Maybe.none()

    def add(self, item):
        new_list = PapaList(self._items)
        new_list._items.append(item)
        return new_list

    def where(self, pred):
        return PapaList([x for x in self._items if pred(x)])

    @property
    def empty(self):
        return len(self._items) == 0

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def __repr__(self):
        return f"[{', '.join(repr(x) for x in self._items)}]"

    def __getitem__(self, index):
        return self.at(index)


class PapaModelInstance:
    """Instance of a PAPA model — dict-like with .field access."""
    def __init__(self, data: dict, model: 'PapaModel'):
        self._data = dict(data)
        self._model = model

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        if name in self._data:
            return self._data[name]
        raise PapaError(f"Поле '{name}' не найдено в {self._model.name}")

    def __repr__(self):
        return f"{{{', '.join(f'{k}: {v!r}' for k, v in self._data.items())}}}"


class PapaModel:
    """PAPA Lang's model — in-memory ORM."""
    _is_papa_model = True

    def __init__(self, name: str, fields: list, interpreter: 'Interpreter'):
        self.name = name
        self.fields = fields  # [(name, type, modifiers), ...]
        self._store = []
        self._interp = interpreter

    def create(self, **kwargs) -> PapaModelInstance:
        data = {}
        for fname, ftype, mods in self.fields:
            if fname in kwargs:
                data[fname] = kwargs[fname]
            else:
                raise PapaError(
                    f"Поле '{fname}' обязательно для {self.name}.create()",
                    hint=f"Укажите: {fname}: значение"
                )
        for k in kwargs:
            if k not in [f[0] for f in self.fields]:
                raise PapaError(f"Неизвестное поле '{k}' в модели {self.name}")
        for fname, ftype, mods in self.fields:
            if 'unique' in mods:
                for rec in self._store:
                    if rec._data.get(fname) == data[fname]:
                        raise PapaError(
                            f"Значение '{data[fname]}' уже существует для уникального поля '{fname}'"
                        )
        inst = PapaModelInstance(data, self)
        self._store.append(inst)
        return inst

    def all(self) -> PapaList:
        return PapaList(list(self._store))

    def find(self, **kwargs) -> Maybe:
        for rec in self._store:
            if all(rec._data.get(k) == v for k, v in kwargs.items()):
                return Maybe.some(rec)
        return Maybe.none()

    def where(self, condition) -> PapaList:
        result = []
        for rec in self._store:
            try:
                env = Environment()
                for k, v in rec._data.items():
                    env.set(k, v)
                if self._interp.evaluate(condition, env):
                    result.append(rec)
            except Exception:
                pass
        return PapaList(result)

    def count(self) -> int:
        return len(self._store)

    def delete(self, rec: PapaModelInstance) -> None:
        if rec in self._store:
            self._store.remove(rec)


class PapaMap:
    """PAPA Lang's map — safe access."""
    def __init__(self, pairs=None):
        self._data = dict(pairs) if pairs else {}

    def get(self, key):
        if key in self._data:
            return Maybe.some(self._data[key])
        return Maybe.none()

    def set(self, key, value):
        new_map = PapaMap(self._data.items())
        new_map._data[key] = value
        return new_map

    @property
    def keys(self):
        return PapaList(self._data.keys())

    @property
    def count(self):
        return len(self._data)

    def __repr__(self):
        pairs = ', '.join(f'{k!r} -> {v!r}' for k, v in self._data.items())
        return '{' + pairs + '}'


# ── Environment ──

class Environment:
    def __init__(self, parent=None):
        self.parent = parent
        self.vars: Dict[str, Any] = {}
        self.mutables: set = set()
        self.functions: Dict[str, FunctionDef] = {}
        self.types: Dict[str, TypeDef] = {}

    def _all_names(self) -> set:
        names = set(self.vars) | set(self.functions)
        if self.parent:
            names |= self.parent._all_names()
        return names

    def get(self, name: str, line: int = 0) -> Any:
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.get(name, line)
        similar = _find_similar_names(name, list(self._all_names()))
        hint = f"Определите переменную: {name} = значение"
        if similar:
            hint += f"\n  💡 Вы имели в виду: {', '.join(similar)}?"
        raise PapaError(
            f"Переменная '{name}' не определена",
            line=line,
            hint=hint
        )

    def set(self, name: str, value: Any, mutable: bool = False):
        self.vars[name] = value
        if mutable:
            self.mutables.add(name)

    def reassign(self, name: str, value: Any, line: int = 0):
        if name in self.vars:
            if name not in self.mutables:
                raise PapaError(
                    f"Переменная '{name}' иммутабельная — нельзя изменить",
                    line=line,
                    hint=f"Используйте 'mut {name} = ...' для мутабельной переменной"
                )
            self.vars[name] = value
            return
        if self.parent:
            self.parent.reassign(name, value, line)
            return
        raise PapaError(f"Переменная '{name}' не определена", line=line)

    def define_function(self, name: str, func: FunctionDef):
        self.functions[name] = func

    def get_function(self, name: str, line: int = 0) -> FunctionDef:
        if name in self.functions:
            return self.functions[name]
        if self.parent:
            return self.parent.get_function(name, line)
        similar = _find_similar_names(name, list(self._all_names()))
        hint = f"Определите функцию: {name}(...) -> ..."
        if similar:
            hint += f"\n  💡 Вы имели в виду: {', '.join(similar)}?"
        raise PapaError(f"Функция '{name}' не определена", line=line, hint=hint)


# ── Interpreter ──

def _to_json_value(val: Any) -> Any:
    """Convert PAPA value to JSON-serializable form."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float, str)):
        return val
    if isinstance(val, Maybe):
        if val.exists:
            return _to_json_value(val.value)
        return None
    if isinstance(val, Secret):
        return "***REDACTED***"
    if isinstance(val, PapaList):
        return [_to_json_value(x) for x in val._items]
    if isinstance(val, PapaMap):
        return {str(k): _to_json_value(v) for k, v in val._data.items()}
    if isinstance(val, dict):
        return {str(k): _to_json_value(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_to_json_value(x) for x in val]
    return str(val)


def _match_route(pattern: str, path: str) -> Optional[Dict[str, str]]:
    """Match route pattern like /users/:id against /users/123. Returns params or None."""
    pattern_parts = pattern.strip('/').split('/')
    path_parts = path.strip('/').split('/')
    if len(pattern_parts) != len(path_parts):
        return None
    params = {}
    for p, v in zip(pattern_parts, path_parts):
        if p.startswith(':'):
            params[p[1:]] = v
        elif p != v:
            return None
    return params


class Interpreter:
    def __init__(self):
        self.global_env = Environment()
        self.output: List[str] = []
        self.routes: Dict[str, RouteDef] = {}
        self.tests: List[TestDef] = []
        self.serve_config: Optional[ServeDef] = None
        self.tasks: List[threading.Thread] = []
        self._imported_files: Set[str] = set()
        self._loaded_modules: Dict[str, Any] = {}
        self._loading_stack: List[str] = []
        self._current_file_dir: str = ""
        self._setup_builtins()

    def _setup_builtins(self):
        """Register built-in functions."""
        self.builtins = {
            'abs': lambda args: abs(args[0]),
            'max': lambda args: max(args[0], args[1]) if len(args) > 1 else max(args[0]),
            'min': lambda args: min(args[0], args[1]) if len(args) > 1 else min(args[0]),
            'len': lambda args: len(args[0]) if hasattr(args[0], '__len__') else args[0].count,
            'str': lambda args: str(args[0]),
            'int': lambda args: int(args[0]),
            'float': lambda args: float(args[0]),
            'range': lambda args: PapaList(range(int(args[0]), int(args[1]) + 1) if len(args) > 1 else range(int(args[0]))),
            'type_of': lambda args: type(args[0]).__name__,
            'some': lambda args: Maybe.some(args[0]),
            'none': lambda args: Maybe.none(),
            'secret': lambda args: Secret(str(args[0])),
            'list': lambda args: PapaList(args[0] if args else []),
            'map': lambda args: PapaMap(),
            'print': lambda args: self._builtin_print(args),
            'input': lambda args: input(args[0] if args else ""),
            'sleep': lambda args: time.sleep(args[0]),
            'now': lambda args: time.strftime("%Y-%m-%d %H:%M:%S"),
            'env': lambda args: self._env_get(args[0]),
            'assert_eq': lambda args: self._builtin_assert_eq(args),
            'assert_true': lambda args: self._builtin_assert_true(args),
            'assert_false': lambda args: self._builtin_assert_false(args),
        }

    def _builtin_print(self, args):
        text = ' '.join(str(a) for a in args)
        self.output.append(text)
        print(text)
        return None

    def _unwrap_for_compare(self, v):
        """Extract comparable value from Maybe, PapaMap items, etc."""
        if hasattr(v, 'value'):
            return v.value
        return v

    def _builtin_assert_eq(self, args):
        if len(args) < 2:
            raise FailSignal("assert_eq требует 2 аргумента")
        a, b = self._unwrap_for_compare(args[0]), self._unwrap_for_compare(args[1])
        if a != b:
            raise FailSignal(f"assert_eq: ожидалось {a!r}, получено {b!r}")

    def _builtin_assert_true(self, args):
        if not args:
            raise FailSignal("assert_true требует 1 аргумент")
        v = self._unwrap_for_compare(args[0])
        if not v:
            raise FailSignal(f"assert_true: ожидалось True, получено {v!r}")

    def _builtin_assert_false(self, args):
        if not args:
            raise FailSignal("assert_false требует 1 аргумент")
        v = self._unwrap_for_compare(args[0])
        if v:
            raise FailSignal(f"assert_false: ожидалось False, получено {v!r}")

    def _env_get(self, name):
        import os
        val = os.environ.get(name)
        if val:
            return Maybe.some(val)
        return Maybe.none()

    def interpret(self, program: Program, filename: str = "") -> Any:
        if filename:
            self._current_file_dir = os.path.dirname(os.path.abspath(filename))
        result = None
        for stmt in program.statements:
            result = self.execute(stmt, self.global_env)
        return result

    def execute(self, node: Any, env: Environment) -> Any:
        if node is None:
            return None

        method_name = f'exec_{type(node).__name__}'
        method = getattr(self, method_name, None)
        if method:
            return method(node, env)

        # Try as expression
        return self.evaluate(node, env)

    def evaluate(self, node: Any, env: Environment) -> Any:
        if node is None:
            return None

        method_name = f'eval_{type(node).__name__}'
        method = getattr(self, method_name, None)
        if method:
            return method(node, env)

        raise PapaError(f"Не могу вычислить: {type(node).__name__}", getattr(node, 'line', 0))

    # ── Expression evaluation ──

    def eval_IntLiteral(self, node: IntLiteral, env: Environment) -> int:
        return node.value

    def eval_FloatLiteral(self, node: FloatLiteral, env: Environment) -> float:
        return node.value

    def eval_TextLiteral(self, node: TextLiteral, env: Environment) -> str:
        text = node.value
        result = []
        i = 0
        while i < len(text):
            if text[i] == '{' and i + 1 < len(text):
                depth = 1
                j = i + 1
                while j < len(text) and depth > 0:
                    if text[j] == '{': depth += 1
                    elif text[j] == '}': depth -= 1
                    j += 1
                expr_str = text[i+1:j-1]
                try:
                    from .lexer import lex as lex_fn
                    from .parser import parse as parse_fn
                    tokens = lex_fn(expr_str)
                    ast = parse_fn(tokens, expr_str)
                    if ast.statements:
                        val = self.evaluate(ast.statements[0], env)
                        result.append(str(val))
                    else:
                        result.append(expr_str)
                except Exception:
                    try:
                        val = env.get(expr_str.strip(), node.line)
                        result.append(str(val))
                    except Exception:
                        result.append('{' + expr_str + '}')
                i = j
            else:
                result.append(text[i])
                i += 1
        return ''.join(result)

    def eval_BoolLiteral(self, node: BoolLiteral, env: Environment) -> bool:
        return node.value

    def eval_NoneLiteral(self, node: NoneLiteral, env: Environment) -> Maybe:
        return Maybe.none()

    def eval_Identifier(self, node: Identifier, env: Environment) -> Any:
        name = node.name
        # Check builtins first
        if name in self.builtins:
            return ('builtin', name)
        # Special keywords as values
        if name == 'true':
            return True
        if name == 'false':
            return False
        # Check functions
        try:
            return env.get_function(name, node.line)
        except PapaError:
            pass
        return env.get(name, node.line)

    def eval_BinaryOp(self, node: BinaryOp, env: Environment) -> Any:
        left = self.evaluate(node.left, env)
        right = self.evaluate(node.right, env)

        ops = {
            '+': lambda a, b: a + b,
            '-': lambda a, b: a - b,
            '*': lambda a, b: a * b,
            '/': lambda a, b: a / b if b != 0 else self._div_zero_error(node),
            '%': lambda a, b: a % b,
            '==': lambda a, b: a == b,
            '!=': lambda a, b: a != b,
            '<': lambda a, b: a < b,
            '>': lambda a, b: a > b,
            '<=': lambda a, b: a <= b,
            '>=': lambda a, b: a >= b,
            'is': lambda a, b: a == b or (isinstance(a, type) and isinstance(b, a)),
            'and': lambda a, b: a and b,
            'or': lambda a, b: a or b,
        }

        if node.op in ops:
            try:
                return ops[node.op](left, right)
            except TypeError as e:
                lt, rt = type(left).__name__, type(right).__name__
                hint = f"Проверьте типы: слева {repr(left)[:30]}, справа {repr(right)[:30]}"
                if node.op == "+" and ("str" in lt or "str" in rt or "text" in str(lt) or "text" in str(rt)):
                    hint = "Преобразуйте: str(42) + \" штук\" или \"{42} штук\""
                raise PapaError(
                    f"Нельзя применить '{node.op}' к {lt} и {rt}",
                    line=node.line,
                    hint=hint
                )

        raise PapaError(f"Неизвестный оператор: {node.op}", line=node.line)

    def _div_zero_error(self, node):
        raise PapaError("Деление на ноль", line=node.line,
                       hint="Проверьте делитель перед делением")

    def eval_UnaryOp(self, node: UnaryOp, env: Environment) -> Any:
        val = self.evaluate(node.operand, env)
        if node.op == '-':
            return -val
        if node.op == 'not':
            return not val
        raise PapaError(f"Неизвестный унарный оператор: {node.op}", line=node.line)

    def eval_FunctionCall(self, node: FunctionCall, env: Environment) -> Any:
        # Member function call: obj.method(args) — eval obj first for model.where special case
        if isinstance(node.name, MemberAccess):
            obj = self.evaluate(node.name.object, env)
            method = node.name.member
            if hasattr(obj, '_is_papa_model') and obj._is_papa_model and method == 'where':
                args = []
            else:
                args = [self.evaluate(a, env) for a in node.args]
            named_args = {k: self.evaluate(v, env) for k, v in (node.named_args or {}).items()}
            return self._call_method(obj, method, args, node.line, named_args, node)

        args = [self.evaluate(a, env) for a in node.args]
        named_args = {k: self.evaluate(v, env) for k, v in (node.named_args or {}).items()}

        # Regular function call
        func = self.evaluate(node.name, env)

        if isinstance(func, tuple) and func[0] == 'builtin':
            return self.builtins[func[1]](args)

        if isinstance(func, FunctionDef):
            if func.is_async:
                def run_async():
                    self._call_function(func, args, env)

                t = threading.Thread(target=run_async, daemon=True)
                t.start()
                self.tasks.append(t)
                return None
            return self._call_function(func, args, env, named_args)

        raise PapaError(
            f"'{node.name}' не является функцией",
            line=node.line,
            hint="Проверьте определение функции"
        )

    def _call_function(self, func: FunctionDef, args: list, env: Environment, named_args: dict = None) -> Any:
        named_args = named_args or {}
        func_env = Environment(parent=env)

        # Bind named args first
        for pname, value in named_args.items():
            func_env.set(pname, value)

        # Bind positional parameters
        for i, (pname, ptype, pdefault) in enumerate(func.params):
            if pname in named_args:
                continue
            if i < len(args):
                value = args[i]
            elif pdefault is not None:
                value = self.evaluate(pdefault, env)
            else:
                raise PapaError(
                    f"Функция '{func.name}' ожидает аргумент '{pname}'",
                    line=func.line,
                    hint=f"Вызов: {func.name}({', '.join(p[0] for p in func.params)})"
                )
            func_env.set(pname, value)

        # Execute body
        try:
            for stmt in func.body:
                self.execute(stmt, func_env)
        except ReturnSignal as ret:
            return ret.value
        except FailSignal:
            if func.can_fail:
                raise
            raise

        return None

    def _call_method(self, obj, method: str, args: list, line: int, named_args: dict = None, call_node=None) -> Any:
        named_args = named_args or {}
        # String methods
        if isinstance(obj, str):
            str_methods = {
                'length': lambda: len(obj),
                'upper': lambda: obj.upper(),
                'lower': lambda: obj.lower(),
                'trim': lambda: obj.strip(),
                'contains': lambda: args[0] in obj if args else False,
                'starts_with': lambda: obj.startswith(args[0]) if args else False,
                'ends_with': lambda: obj.endswith(args[0]) if args else False,
                'repeat': lambda: obj * int(args[0]) if args else obj,
                'chars': lambda: PapaList(list(obj)),
                'index_of': lambda: obj.find(args[0]) if args else -1,
                'split': lambda: PapaList(obj.split(args[0]) if args else obj.split()),
                'replace': lambda: obj.replace(args[0], args[1]) if len(args) >= 2 else obj,
            }
            if method in str_methods:
                return str_methods[method]()

        # List methods
        if isinstance(obj, PapaList):
            list_methods = {
                'add': lambda: obj.add(args[0]) if args else obj,
                'at': lambda: obj.at(int(args[0])) if args else Maybe.none(),
                'contains': lambda: args[0] in obj._items if args else False,
                'join': lambda: args[0].join(str(x) for x in obj._items) if args else ', '.join(str(x) for x in obj._items),
                'reverse': lambda: PapaList(list(reversed(obj._items))),
                'sort': lambda: PapaList(sorted(obj._items)),
            }
            if method in list_methods:
                return list_methods[method]()

        # Maybe methods
        if isinstance(obj, Maybe):
            if method == 'value':
                return obj.value
            if method == 'exists':
                return obj.exists

        # Map methods
        if isinstance(obj, PapaMap):
            if method == 'get':
                return obj.get(args[0]) if args else Maybe.none()
            if method == 'set':
                return obj.set(args[0], args[1]) if len(args) >= 2 else obj

        # Model methods
        if hasattr(obj, '_is_papa_model') and obj._is_papa_model:
            if method == 'create':
                return obj.create(**named_args)
            if method == 'all':
                return obj.all()
            if method == 'count':
                return obj.count()
            if method == 'find':
                return obj.find(**named_args)
            if method == 'where':
                if call_node and call_node.args:
                    return obj.where(call_node.args[0])
                raise PapaError("where() требует условие", line=line, hint="User.where(age >= 18)")
            if method == 'delete':
                if args:
                    obj.delete(args[0])
                    return None
                raise PapaError("delete() требует запись", line=line)

        # Dict-like access
        if isinstance(obj, dict):
            if method in obj:
                return obj[method]

        raise PapaError(
            f"Метод '{method}' не найден для типа {type(obj).__name__}",
            line=line,
            hint=f"Доступные методы зависят от типа объекта"
        )

    def eval_MemberAccess(self, node: MemberAccess, env: Environment) -> Any:
        obj = self.evaluate(node.object, env)

        # Dict access
        if isinstance(obj, dict):
            if node.member in obj:
                return obj[node.member]
            return Maybe.none()

        # PapaMap
        if isinstance(obj, PapaMap):
            return obj.get(node.member)

        # PapaList properties
        if isinstance(obj, PapaList):
            props = {'count': obj.count, 'first': obj.first, 'last': obj.last, 'empty': obj.empty}
            if node.member in props:
                return props[node.member]

        # Maybe properties
        if isinstance(obj, Maybe):
            if node.member == 'exists':
                return obj.exists
            if node.member == 'value':
                return obj.value

        # String properties
        if isinstance(obj, str):
            if node.member == 'length':
                return len(obj)
            if node.member == 'empty':
                return len(obj) == 0

        # Generic attribute access
        if hasattr(obj, node.member):
            return getattr(obj, node.member)

        raise PapaError(
            f"Свойство '{node.member}' не найдено",
            line=node.line,
            hint=f"Объект типа {type(obj).__name__} не имеет свойства '{node.member}'"
        )

    def eval_OptionalChain(self, node: OptionalChain, env: Environment) -> Any:
        obj = self.evaluate(node.object, env)
        if isinstance(obj, Maybe):
            if not obj.exists:
                return Maybe.none()
            obj = obj.value
        if obj is None:
            return Maybe.none()
        try:
            result = self.eval_MemberAccess(
                MemberAccess(object=node.object, member=node.member, line=node.line),
                env
            )
            return Maybe.some(result)
        except PapaError:
            return Maybe.none()

    def eval_NullCoalesce(self, node: NullCoalesce, env: Environment) -> Any:
        left = self.evaluate(node.expr, env)
        if isinstance(left, Maybe):
            if left.exists:
                return left.value
            return self.evaluate(node.default, env)
        if left is None:
            return self.evaluate(node.default, env)
        return left

    def eval_ListLiteral(self, node: ListLiteral, env: Environment) -> PapaList:
        elements = [self.evaluate(e, env) for e in node.elements]
        return PapaList(elements)

    def eval_MapLiteral(self, node: MapLiteral, env: Environment) -> PapaMap:
        result_pairs = []
        for k, v in node.pairs:
            if isinstance(k, Identifier):
                key_val = k.name
            else:
                key_val = self.evaluate(k, env)
            result_pairs.append((key_val, self.evaluate(v, env)))
        return PapaMap(result_pairs)

    def eval_RangeLiteral(self, node: RangeLiteral, env: Environment) -> PapaList:
        start = self.evaluate(node.start, env)
        end = self.evaluate(node.end, env)
        return PapaList(list(range(int(start), int(end) + 1)))

    def eval_IndexAccess(self, node: IndexAccess, env: Environment) -> Any:
        obj = self.evaluate(node.object, env)
        index = self.evaluate(node.index, env)
        if isinstance(obj, PapaList):
            return obj.at(int(index))
        if isinstance(obj, PapaMap):
            return obj.get(index)
        if isinstance(obj, list):
            idx = int(index)
            if 0 <= idx < len(obj):
                return Maybe.some(obj[idx])
            return Maybe.none()
        if isinstance(obj, str):
            idx = int(index)
            if 0 <= idx < len(obj):
                return obj[idx]
            return Maybe.none()
        raise PapaError(f"Тип {type(obj).__name__} не поддерживает индексацию", line=node.line)

    # ── Statement execution ──

    def exec_Assignment(self, node: Assignment, env: Environment) -> None:
        value = self.evaluate(node.value, env)
        env.set(node.name, value, mutable=node.mutable)

    def exec_Reassignment(self, node: Reassignment, env: Environment) -> None:
        value = self.evaluate(node.value, env)
        if isinstance(node.target, Identifier):
            env.reassign(node.target.name, value, line=node.line)
        else:
            raise PapaError("Нельзя присвоить значение этому выражению", line=node.line)

    def exec_SayStatement(self, node: SayStatement, env: Environment) -> None:
        value = self.evaluate(node.expr, env)
        text = str(value)
        self.output.append(text)
        print(text)

    def exec_LogStatement(self, node: LogStatement, env: Environment) -> None:
        value = self.evaluate(node.expr, env)
        timestamp = time.strftime("%H:%M:%S")
        level_icons = {'info': 'ℹ️', 'warn': '⚠️', 'error': '❌', 'debug': '🔧', 'fatal': '💀'}
        icon = level_icons.get(node.level, 'ℹ️')
        text = f"[{timestamp}] {icon} {node.level.upper()}: {value}"
        self.output.append(text)
        print(text)

    def exec_ReturnStatement(self, node: ReturnStatement, env: Environment):
        value = self.evaluate(node.value, env) if node.value else None
        raise ReturnSignal(value)

    def exec_FailStatement(self, node: FailStatement, env: Environment):
        message = self.evaluate(node.message, env)
        raise FailSignal(str(message), line=node.line)

    def exec_IfStatement(self, node: IfStatement, env: Environment) -> Any:
        condition = self.evaluate(node.condition, env)

        # Handle maybe as condition
        if isinstance(condition, Maybe):
            condition = condition.exists

        if condition:
            for stmt in node.body:
                self.execute(stmt, env)
        else:
            for elif_cond, elif_body in node.elif_branches:
                cond = self.evaluate(elif_cond, env)
                if isinstance(cond, Maybe):
                    cond = cond.exists
                if cond:
                    for stmt in elif_body:
                        self.execute(stmt, env)
                    return
            for stmt in node.else_body:
                self.execute(stmt, env)

    def exec_MatchStatement(self, node: MatchStatement, env: Environment) -> Any:
        value = self.evaluate(node.expr, env)
        for pattern, body in node.arms:
            if self._match_pattern(value, pattern, env):
                result = None
                for stmt in body:
                    result = self.execute(stmt, env)
                return result
        raise PapaError(
            f"Ни один паттерн не совпал в match для значения: {value!r}",
            line=node.line,
            hint="Добавьте обработку всех возможных вариантов"
        )

    def _match_pattern(self, value, pattern, env) -> bool:
        if isinstance(pattern, Identifier):
            if pattern.name == 'some' and isinstance(value, Maybe) and value.exists:
                return True
            if pattern.name == 'none' and isinstance(value, Maybe) and not value.exists:
                return True
            if pattern.name == '_':
                return True
            pat_val = self.evaluate(pattern, env)
            return value == pat_val
        pat_val = self.evaluate(pattern, env)
        return value == pat_val

    def exec_ForLoop(self, node: ForLoop, env: Environment) -> None:
        iterable = self.evaluate(node.iterable, env)

        if isinstance(iterable, PapaList):
            items = iterable._items
        elif isinstance(iterable, list):
            items = iterable
        elif isinstance(iterable, range):
            items = iterable
        elif isinstance(iterable, str):
            items = list(iterable)
        else:
            raise PapaError(
                f"Нельзя итерировать по типу {type(iterable).__name__}",
                line=node.line,
                hint="Используйте список, диапазон (1..10) или текст"
            )

        # Use parent env directly so reassignment works on outer scope
        env.set(node.var, None, mutable=True)
        index_var = getattr(node, 'index_var', None)
        if index_var:
            env.set(index_var, 0, mutable=True)
        for i, item in enumerate(items):
            if index_var:
                env.vars[index_var] = i
            env.vars[node.var] = item
            try:
                for stmt in node.body:
                    self.execute(stmt, env)
            except BreakSignal:
                break

    def exec_LoopStatement(self, node: LoopStatement, env: Environment) -> None:
        loop_env = Environment(parent=env)
        while True:
            try:
                for stmt in node.body:
                    self.execute(stmt, loop_env)
            except BreakSignal:
                break

    def exec_RepeatStatement(self, node: RepeatStatement, env: Environment) -> None:
        count = self.evaluate(node.count, env)
        completed = False
        for i in range(int(count)):
            try:
                for stmt in node.body:
                    self.execute(stmt, env)
                completed = True
            except BreakSignal:
                completed = True
                break
        if not completed and node.else_body:
            for stmt in node.else_body:
                self.execute(stmt, env)

    def exec_WaitStatement(self, node: WaitStatement, env: Environment) -> None:
        duration = self.evaluate(node.duration, env)
        multipliers = {'seconds': 1, 'minutes': 60, 'hours': 3600, 'days': 86400}
        seconds = float(duration) * multipliers.get(node.unit, 1)
        time.sleep(seconds)

    def exec_AssertStatement(self, node: AssertStatement, env: Environment) -> None:
        result = self.evaluate(node.expr, env)
        if isinstance(result, Maybe):
            result = result.exists
        if not result:
            raise PapaError(
                f"Утверждение не выполнено",
                line=node.line,
                hint="Проверьте условие в assert"
            )

    def exec_FunctionDef(self, node: FunctionDef, env: Environment) -> None:
        env.define_function(node.name, node)

    def exec_TypeDef(self, node: TypeDef, env: Environment) -> None:
        env.types[node.name] = node

    def exec_ModelDef(self, node: ModelDef, env: Environment) -> None:
        model = PapaModel(node.name, node.fields, self)
        env.set(node.name, model)

    def exec_EnumDef(self, node: 'EnumDef', env: Environment) -> None:
        enum_map = PapaMap([(v, v) for v in node.variants])
        env.set(node.name, enum_map)

    def exec_ServeDef(self, node: ServeDef, env: Environment) -> None:
        self.serve_config = node
        text = f"🚀 Сервер настроен на порту {node.port}"
        self.output.append(text)
        print(text)

    def exec_RouteDef(self, node: RouteDef, env: Environment) -> None:
        key = f"{node.method} {node.path}"
        self.routes[key] = node
        auth_str = " 🔒" if node.auth_required else ""
        text = f"  📡 {node.method} {node.path}{auth_str}"
        self.output.append(text)
        print(text)

    def exec_TestDef(self, node: TestDef, env: Environment) -> None:
        self.tests.append(node)

    def exec_TaskDef(self, node: TaskDef, env: Environment) -> None:
        def run_task():
            task_env = Environment(parent=env)
            try:
                for stmt in node.body:
                    self.execute(stmt, task_env)
            except Exception:
                pass

        t = threading.Thread(target=run_task, daemon=True)
        t.start()
        self.tasks.append(t)

    def exec_EveryDef(self, node: EveryDef, env: Environment) -> None:
        def run_every():
            multipliers = {'seconds': 1, 'minutes': 60, 'hours': 3600, 'days': 86400}
            interval_val = self.evaluate(node.interval, env)
            seconds = float(interval_val) * multipliers.get(node.unit, 1)

            def tick():
                while True:
                    time.sleep(seconds)
                    every_env = Environment(parent=env)
                    try:
                        for stmt in node.body:
                            self.execute(stmt, every_env)
                    except Exception:
                        pass

            t = threading.Thread(target=tick, daemon=True)
            t.start()
            self.tasks.append(t)

        run_every()

    def _resolve_import_path(self, path: str) -> tuple:
        """Resolve import path relative to current file or as std module."""
        if path.startswith("std/"):
            name = path[4:].split("/")[0].split(".")[0]
            if name in STD_MODULE_LOADERS:
                return ("std", name, None)
            raise PapaError(
                f"Стандартный модуль '{path}' не найден",
                hint="Доступны: std/math, std/string, std/json, std/http, std/fs, std/time, std/voice, std/mcp, std/browser, std/telegram, std/ai, std/design"
            )
        base = self._current_file_dir or os.getcwd()
        full = os.path.normpath(os.path.join(base, path))
        if not full.endswith('.papa'):
            full += '.papa'
        if os.path.exists(full):
            return ("file", full, full)
        # Проверить papa_modules/
        proj_root = self._find_project_root(base)
        if proj_root:
            parts = path.replace("\\", "/").split("/")
            pkg_dir = os.path.join(proj_root, "papa_modules", parts[0])
            if len(parts) == 1:
                idx = os.path.join(pkg_dir, "index.papa")
                if os.path.isfile(idx):
                    return ("file", idx, idx)
                if os.path.isfile(pkg_dir + ".papa"):
                    return ("file", pkg_dir + ".papa", pkg_dir + ".papa")
            else:
                subpath = os.path.join(pkg_dir, *parts[1:])
                if not subpath.endswith(".papa"):
                    subpath += ".papa"
                if os.path.isfile(subpath):
                    return ("file", subpath, subpath)
        raise PapaError(
            f"Модуль не найден: {path}",
            hint=f"Проверьте путь или papa install <package>"
        )

    def _find_project_root(self, start: str) -> Optional[str]:
        """Ищем корень проекта (где papa.toml или papa_modules)."""
        current = os.path.abspath(start)
        while current and current != os.path.dirname(current):
            if os.path.isfile(os.path.join(current, "papa.toml")):
                return current
            if os.path.isdir(os.path.join(current, "papa_modules")):
                return current
            current = os.path.dirname(current)
        return None

    def _load_module(self, path: str) -> tuple:
        """Load and execute a .papa file. Returns (env, path). Prevents cycle imports."""
        resolved = self._resolve_import_path(path)
        if resolved[0] == "std":
            _, name, _ = resolved
            cache_key = "std:" + name
            if cache_key in self._loaded_modules:
                return self._loaded_modules[cache_key], path
            if cache_key in self._loading_stack:
                raise PapaError(
                    f"Циклический импорт: {path}",
                    hint="Уберите циклическую зависимость между файлами"
                )
            self._loading_stack.append(cache_key)
            import_env = Environment(parent=self.global_env)
            exports = STD_MODULE_LOADERS[name](self)
            for k, v in exports.items():
                if isinstance(v, tuple) and v[0] == "builtin":
                    import_env.vars[k] = v
                else:
                    import_env.vars[k] = v  # constants like pi, e
            self._loading_stack.pop()
            self._loaded_modules[cache_key] = import_env
            return import_env, path

        full_path = resolved[2]
        if full_path in self._loaded_modules:
            return self._loaded_modules[full_path], path
        if full_path in self._loading_stack:
            raise PapaError(
                f"Циклический импорт: {path}",
                hint="Уберите циклическую зависимость между файлами"
            )
        self._loading_stack.append(full_path)
        with open(full_path, 'r', encoding='utf-8') as f:
            source = f.read()
        from .lexer import lex
        from .parser import parse
        tokens = lex(source, full_path)
        ast = parse(tokens, source)
        import_env = Environment(parent=self.global_env)
        orig_dir = self._current_file_dir
        self._current_file_dir = os.path.dirname(full_path)
        try:
            for stmt in ast.statements:
                self.execute(stmt, import_env)
        finally:
            self._current_file_dir = orig_dir
            self._loading_stack.pop()
        self._loaded_modules[full_path] = import_env
        return import_env, path

    def exec_ImportStatement(self, node: 'ImportStatement', env: Environment) -> None:
        import_env, _ = self._load_module(node.path)
        for name, val in import_env.vars.items():
            env.vars[name] = val
        for name, func in import_env.functions.items():
            env.functions[name] = func

    def exec_FromImportStatement(self, node: 'FromImportStatement', env: Environment) -> None:
        import_env, _ = self._load_module(node.path)
        for name in node.names:
            if name in import_env.vars:
                env.vars[name] = import_env.vars[name]
            elif name in import_env.functions:
                env.functions[name] = import_env.functions[name]
            else:
                raise PapaError(
                    f"'{name}' не найден в модуле {node.path}",
                    line=node.line,
                    hint=f"Проверьте экспорт в файле {node.path}"
                )

    def run_tests(self) -> tuple:
        """Run all registered tests. Returns (passed, failed, results)."""
        passed = 0
        failed = 0
        results = []

        for test in self.tests:
            test_env = Environment(parent=self.global_env)
            try:
                for stmt in test.body:
                    self.execute(stmt, test_env)
                passed += 1
                results.append(('✅', test.name, None))
                print(f"  ✅ {test.name}")
            except Exception as e:
                failed += 1
                results.append(('❌', test.name, str(e)))
                print(f"  ❌ {test.name}: {e}")

        print(f"\n  Результат: {passed} прошло, {failed} провалено")
        return passed, failed, results

    # ── HTTP Server (v0.3) ──

    def _create_handler(self):
        """Create HTTP request handler with access to interpreter."""
        interp = self
        routes_map = dict(self.routes)

        class PapaHTTPHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] 🌐 {self.command} {self.path} -> {args[0] if args else ''}")

            def _send_cors(self):
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

            def _send_json(self, data: Any, status: int = 200):
                body = json.dumps(data, ensure_ascii=False).encode('utf-8')
                self.send_response(status)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self._send_cors()
                self.send_header('Content-Length', len(body))
                self.end_headers()
                self.wfile.write(body)

            def _handle_route(self, method: str, path: str) -> Optional[Tuple[Any, int]]:
                parsed = urlparse(path)
                path_only = parsed.path or '/'

                for route_key, route_def in routes_map.items():
                    rt_method, rt_pattern = route_key.split(' ', 1)
                    if rt_method != method:
                        continue
                    params = _match_route(rt_pattern, path_only)
                    if params is not None:
                        return (route_def, params)
                return None

            def do_OPTIONS(self):
                self.send_response(204)
                self._send_cors()
                self.end_headers()

            def do_GET(self):
                self._do_request('GET')

            def do_POST(self):
                self._do_request('POST')

            def do_PUT(self):
                self._do_request('PUT')

            def do_DELETE(self):
                self._do_request('DELETE')

            def _do_request(self, method: str):
                parsed = urlparse(self.path)
                path_only = parsed.path or '/'

                match = self._handle_route(method, path_only)
                if not match:
                    self._send_json({'error': 'Not Found'}, 404)
                    return

                route_def, params = match
                if route_def.auth_required:
                    auth = self.headers.get('Authorization', '')
                    if not auth or not auth.startswith('Bearer '):
                        self._send_json({'error': 'Unauthorized'}, 401)
                        return

                env = Environment(parent=interp.global_env)
                for k, v in params.items():
                    env.set(k, v)

                if method in ('POST', 'PUT') and self.headers.get('Content-Length'):
                    try:
                        length = int(self.headers.get('Content-Length', 0))
                        body_raw = self.rfile.read(length).decode('utf-8')
                        if body_raw.strip():
                            body_data = json.loads(body_raw)
                            body_papa = interp._py_to_papa(body_data)
                            env.set('body', body_papa)
                        else:
                            env.set('body', None)
                    except Exception:
                        env.set('body', None)
                else:
                    env.set('body', None)

                try:
                    result = None
                    try:
                        for stmt in route_def.body:
                            result = interp.execute(stmt, env)
                    except ReturnSignal as ret:
                        result = ret.value
                    out = _to_json_value(result)
                    self._send_json(out)
                except Exception as e:
                    self._send_json({'error': str(e)}, 500)

        return PapaHTTPHandler

    def _py_to_papa(self, val: Any) -> Any:
        """Convert Python/JSON value to PAPA type."""
        if val is None:
            return Maybe.none()
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return val
        if isinstance(val, str):
            return val
        if isinstance(val, list):
            return PapaList([self._py_to_papa(x) for x in val])
        if isinstance(val, dict):
            return PapaMap([(k, self._py_to_papa(v)) for k, v in val.items()])
        return val

    def start_server(self):
        """Start HTTP server with registered routes."""
        if not self.serve_config:
            raise PapaError("Сервер не настроен", hint="Добавьте 'serve on port N' в программу")
        port = self.serve_config.port
        handler = self._create_handler()
        server = HTTPServer(('', port), handler)
        print(f"\n🌐 Сервер запущен на http://localhost:{port}/")
        print("  Нажмите Ctrl+C для остановки\n")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Сервер остановлен")
            server.shutdown()


def run(source: str, filename: str = "<stdin>") -> Interpreter:
    """Convenience function to lex, parse, and interpret PAPA Lang code."""
    from .lexer import lex
    from .parser import parse

    tokens = lex(source, filename)
    ast = parse(tokens, source)
    interp = Interpreter()
    interp.interpret(ast)
    return interp
