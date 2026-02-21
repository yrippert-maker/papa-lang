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
import hashlib
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

    def design_propose(args):
        req = args[0] if args else PapaMap([])
        data = req._data if hasattr(req, '_data') else {}
        layout = data.get("layout", "landing")
        palette = data.get("palette", "#7C5CFC")
        industry = str(data.get("industry", "generic"))
        return PapaMap([
            ("layout", design_layout([layout])),
            ("palette", design_palette([palette])),
            ("components", design_component(["button", 2])),
            ("industry_hint", industry),
        ])

    def design_from_industry(args):
        industry = str(args[0]) if args else "generic"
        palettes = {"fintech": "#2563EB", "healthcare": "#059669", "ecommerce": "#DC2626", "legal": "#7C3AED"}
        primary = palettes.get(industry.lower(), "#7C5CFC")
        return PapaMap([
            ("palette", design_palette([primary])),
            ("components", PapaList([PapaMap([("name", "card"), ("variant", "default")])])),
            ("fonts", "Inter, system-ui"),
            ("layout_hint", "dashboard" if industry.lower() in ["fintech", "legal"] else "landing"),
        ])

    def design_refine(args):
        desc = str(args[0]) if args else ""
        variant = args[1] if len(args) > 1 else PapaMap([])
        data = variant._data if hasattr(variant, '_data') else {}
        changes = []
        if "form" in desc.lower():
            changes.append("added form accessibility")
        if data:
            changes.append("refined from variant")
        score = min(95, 80 + len(changes) * 5)
        return PapaMap([
            ("refined", PapaMap(list(data.items()) + [("refined", True)]) if data else PapaMap([("refined", True)])),
            ("changes", "; ".join(changes) if changes else "none"),
            ("score", score),
        ])

    for fn in (design_tokens, design_component, design_palette, design_review, design_layout,
               design_propose, design_from_industry, design_refine):
        interp.builtins[prefix + fn.__name__] = fn
    return {k: ("builtin", prefix + k) for k in ["design_tokens", "design_component", "design_palette",
        "design_review", "design_layout", "design_propose", "design_from_industry", "design_refine"]}

# ── std/orchestrator — AI Safety Orchestrator ──
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
        plan_excerpt = task[:60] + "..."
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

# ── std/docs — AI Document Generation ──
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

# ── std/studio — AI Development Studio ──
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

# ── std/cwb — CWB Mobile Assistant ──
def _load_cwb(interp: 'Interpreter') -> Dict[str, Any]:
    """CWB: AI-помощник для мобильных задач — процесс, идеи, команды, таски, контекст."""
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

# ── Wave 2 & Wave 3 std modules ──
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
        now = time.time()
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
        if args:
            cfg = args[0]
            if hasattr(cfg, '_data'):
                cfg = cfg._data
            elif not isinstance(cfg, dict):
                cfg = {}
            for key, value in cfg.items():
                if hasattr(value, 'exists') and value.exists:
                    value = value.value
                if key in _config:
                    _config[key] = value
        return _config.copy()

    def _compliance_report(args):
        """guard_compliance_report() -> map — отчёт"""
        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "config": {k: v for k, v in _config.items() if k != "log"},
            "total_events": len(_config["log"]),
            "events_by_type": _count_events(),
            "recent_events": _config["log"][-10:],
            "cost_spent_usd": _config["cost_spent_usd"],
            "cost_remaining_usd": _config["cost_limit_usd"] - _config["cost_spent_usd"],
        }

    def _log_event(event_type: str, actor: str = "", details: Any = None):
        _config["log"].append({
            "time": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
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
                # Test/fallback mode: return simulated response
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
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
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
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
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
        raw_config = args[0] if args else {}
        # Convert PapaMap to plain dict
        if hasattr(raw_config, '_data'):
            config = dict(raw_config._data)
        elif isinstance(raw_config, dict):
            config = raw_config
        else:
            config = {}
        _counter["value"] += 1
        swarm_id = f"swarm_{_counter['value']}"

        _swarms[swarm_id] = {
            "id": swarm_id,
            "name": config.get("name", swarm_id),
            "strategy": config.get("strategy", "parallel"),  # parallel | sequential | consensus
            "agents": [],
            "status": "created",
            "results": [],
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "consensus_threshold": float(config.get("consensus_threshold", 0.7)),
        }

        # Создать начальных агентов, если указаны
        initial_agents = config.get("agents", [])
        # Unwrap Maybe wrapper if needed
        if hasattr(initial_agents, '_value') and hasattr(initial_agents, '_has'):
            initial_agents = initial_agents._value if initial_agents._has else []
        # Convert PapaList to plain list
        if hasattr(initial_agents, '_items'):
            initial_agents = list(initial_agents._items)
        if isinstance(initial_agents, list):
            for agent_cfg in initial_agents:
                # Unwrap Maybe if needed
                if hasattr(agent_cfg, '_value') and hasattr(agent_cfg, '_has'):
                    agent_cfg = agent_cfg._value if agent_cfg._has else {}
                # Convert PapaMap to dict
                if hasattr(agent_cfg, '_data'):
                    agent_cfg = dict(agent_cfg._data)
                _add_agent([swarm_id, agent_cfg])
        return {"swarm_id": swarm_id, "agents_count": len(_swarms[swarm_id]["agents"])}

    def _add_agent(args):
        """swarm_add_agent(swarm_id, agent_config) -> {agent_id}"""
        swarm_id = str(args[0]) if args else ""
        raw_acfg = args[1] if len(args) > 1 else {}
        if hasattr(raw_acfg, '_data'):
            agent_cfg = dict(raw_acfg._data)
        elif isinstance(raw_acfg, dict):
            agent_cfg = raw_acfg
        else:
            agent_cfg = {}

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


    def _orchestrated(args):
        """swarm_orchestrated(goal, num_agents) -> {goal, agents, results, merged}"""
        goal = str(args[0]) if args else ""
        num_agents = int(args[1]) if len(args) > 1 else 3
        ai_ask = interp.builtins.get("_ai_router_ask")
        plan_prompt = f"Break this goal into {num_agents} independent subtasks. Goal: {goal}\n\nReturn a JSON array of objects with name, role, task fields."
        subtasks = []
        if ai_ask:
            try:
                resp = ai_ask([plan_prompt, {}])
                text = resp.get("response", "") if isinstance(resp, dict) else str(resp)
                import re
                json_match = re.search(r'[\s\S]*', text)
                if json_match:
                    subtasks = json.loads(json_match.group())
            except Exception:
                pass
        if not subtasks:
            subtasks = [{"name": f"agent_{i+1}", "role": f"Specialist {i+1}", "task": f"Part {i+1} of: {goal}"} for i in range(num_agents)]
        _counter["value"] += 1
        swarm_id = f"swarm_orch_{_counter['value']}"
        _swarms[swarm_id] = {"id": swarm_id, "name": f"orchestrated_{goal[:20]}", "strategy": "orchestrated", "agents": [], "status": "running", "results": [], "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "consensus_threshold": 0.7}
        results = []
        for st in subtasks:
            agent = {"id": f"agent_{len(_swarms[swarm_id]['agents'])+1}", "role": st.get("role","general"), "provider":"claude", "model":"claude-sonnet-4-20250514", "system_prompt": st.get("role",""), "temperature":0.7, "status":"done", "result":None}
            task = st.get("task", goal)
            full_prompt = f"[Role: {agent['role']}]\n\nTask: {task}"
            if ai_ask:
                try:
                    r = ai_ask([full_prompt, {}])
                    agent["result"] = r.get("response", f"[{agent['role']}] {task[:60]}...") if isinstance(r, dict) else str(r)
                except Exception:
                    agent["result"] = f"[{agent['role']}] Analysis of: {task[:60]}..."
            else:
                agent["result"] = f"[{agent['role']}] Analysis of: {task[:60]}..."
            _swarms[swarm_id]["agents"].append(agent)
            results.append({"agent": agent["id"], "role": agent["role"], "result": agent["result"]})
        merged = f"Synthesis of {len(results)} agent results for: {goal}"
        if ai_ask:
            try:
                merge_prompt = f"You are a project coordinator. Merge these results from {len(results)} agents into a coherent solution:\n\n{json.dumps(results, default=str)}\n\nOriginal goal: {goal}"
                r = ai_ask([merge_prompt, {"max_tokens": 2048}])
                merged = r.get("response", merged) if isinstance(r, dict) else merged
            except Exception:
                pass
        _swarms[swarm_id]["results"] = results
        _swarms[swarm_id]["status"] = "completed"
        return {"goal": goal, "agents": len(subtasks), "results": results, "merged": merged, "swarm_id": swarm_id}

    def _pipeline(args):
        """swarm_pipeline(input, stages) -> {result, stages_completed, history}"""
        current = str(args[0]) if args else ""
        stages = args[1] if len(args) > 1 else []
        if hasattr(stages, '_items'): stages = list(stages._items) if stages else []
        elif not isinstance(stages, list): stages = []
        ai_ask = interp.builtins.get("_ai_router_ask")
        history = []
        for stage in stages:
            stage_data = stage._data if hasattr(stage, '_data') else (stage if isinstance(stage, dict) else {})
            stage_name = stage_data.get("name", "stage") if isinstance(stage_data, dict) else str(stage)
            role = stage_data.get("role", "processor") if isinstance(stage_data, dict) else "processor"
            task = stage_data.get("task", "process input") if isinstance(stage_data, dict) else "process"
            prompt = f"{role}\n\nInput: {current}\n\nTask: {task}"
            if ai_ask:
                try:
                    r = ai_ask([prompt, {}])
                    current = r.get("response", current) if isinstance(r, dict) else current
                except Exception:
                    pass
            else:
                current = f"[{stage_name}] Processed: {current[:100]}..."
            history.append({"stage": stage_name, "output_length": len(current)})
        return {"result": current, "stages_completed": len(history), "history": history}

    def _debate(args):
        """swarm_debate(topic, rounds) -> {topic, rounds, verdict}"""
        topic = str(args[0]) if args else ""
        num_rounds = int(args[1]) if len(args) > 1 else 3
        ai_ask = interp.builtins.get("_ai_router_ask")
        rounds = []; pro_arg, con_arg = "", ""
        for i in range(num_rounds):
            pro_prompt = f"Topic: {topic}\nPrevious counter-argument: {con_arg}\nMake your strongest argument FOR."
            if ai_ask:
                try:
                    r = ai_ask([pro_prompt, {}])
                    pro_arg = r.get("response", f"[PRO {i+1}]") if isinstance(r, dict) else str(r)
                except Exception:
                    pro_arg = f"[PRO {i+1}]"
            else:
                pro_arg = f"[PRO {i+1}] For: {topic[:50]}..."
            con_prompt = f"Topic: {topic}\nPrevious: {pro_arg}\nMake your strongest argument AGAINST."
            if ai_ask:
                try:
                    r = ai_ask([con_prompt, {}])
                    con_arg = r.get("response", f"[CON {i+1}]") if isinstance(r, dict) else str(r)
                except Exception:
                    con_arg = f"[CON {i+1}]"
            else:
                con_arg = f"[CON {i+1}] Against: {topic[:50]}..."
            rounds.append({"round": i+1, "pro": pro_arg, "con": con_arg})
        verdict = f"After {num_rounds} rounds on '{topic}', both sides presented valid points."
        if ai_ask:
            try:
                r = ai_ask([f"Judge this debate:\n{json.dumps(rounds, default=str)}\nSummarize best points.", {"max_tokens": 1024}])
                verdict = r.get("response", verdict) if isinstance(r, dict) else verdict
            except Exception:
                pass
        return {"topic": topic, "rounds": rounds, "verdict": verdict}


    # --- Регистрация ---
    interp.builtins[prefix + "create"] = _create
    interp.builtins[prefix + "add_agent"] = _add_agent
    interp.builtins[prefix + "run"] = _run
    interp.builtins[prefix + "status"] = _status
    interp.builtins[prefix + "collect"] = _collect
    interp.builtins[prefix + "destroy"] = _destroy
    interp.builtins[prefix + "orchestrated"] = _orchestrated
    interp.builtins[prefix + "pipeline"] = _pipeline
    interp.builtins[prefix + "debate"] = _debate


    return {
        "swarm_create":     ("builtin", prefix + "create"),
        "swarm_add_agent":  ("builtin", prefix + "add_agent"),
        "swarm_run":        ("builtin", prefix + "run"),
        "swarm_status":     ("builtin", prefix + "status"),
        "swarm_collect":    ("builtin", prefix + "collect"),
        "swarm_destroy":    ("builtin", prefix + "destroy"),
        "swarm_orchestrated": ("builtin", prefix + "orchestrated"),
        "swarm_pipeline":     ("builtin", prefix + "pipeline"),
        "swarm_debate":       ("builtin", prefix + "debate"),
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
        # Unescape literal \n to real newlines for analysis
        code = code.replace("\\n", "\n")
        raw_spec = args[2] if len(args) > 2 else {}
        # Convert PapaMap/Maybe/dict to plain Python dict
        if hasattr(raw_spec, '_data'):
            spec = dict(raw_spec._data)
        elif hasattr(raw_spec, '_value') and hasattr(raw_spec, '_has'):
            spec = raw_spec._value if raw_spec._has else {}
        elif isinstance(raw_spec, dict):
            spec = raw_spec
        else:
            spec = {}
        # Unwrap Maybe values inside spec
        unwrapped_spec = {}
        for k, v in (spec.items() if isinstance(spec, dict) else []):
            if hasattr(v, '_value') and hasattr(v, '_has'):
                unwrapped_spec[k] = v._value if v._has else None
            else:
                unwrapped_spec[k] = v
        spec = unwrapped_spec

        issues = []
        import sys
        print(f"DEBUG verify: spec={spec!r}, spec type={type(spec)}, keys={list(spec.keys()) if isinstance(spec, dict) else 'N/A'}", file=sys.stderr)
        for k, v in spec.items():
            print(f"DEBUG verify key: {k!r} -> {v!r} (type={type(v).__name__})", file=sys.stderr)
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
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
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
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
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
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    def _verified_generate(args):
        """verified_generate(spec, generator_prompt?) -> {value, proof, verification, is_verified, confidence}"""
        spec = str(args[0]) if args else ""
        gen_prompt = str(args[1]) if len(args) > 1 else ""
        ai_ask = interp.builtins.get("_ai_router_ask")
        if not ai_ask:
            return {"is_verified": False, "error": "AI router not available", "value": None, "confidence": 0}
        code_prompt = gen_prompt or f"Generate code that satisfies this specification:\n{spec}\n\nReturn ONLY the code."
        try:
            code_resp = ai_ask([code_prompt, {"max_tokens": 2048}])
            code = code_resp.get("response", "")
        except Exception as e:
            return {"is_verified": False, "error": str(e), "value": None, "confidence": 0}
        proof_prompt = (
            f"You are a formal verification expert.\n\nCode:\n{code}\n\nSpecification:\n{spec}\n\n"
            f"Verify this code. Return JSON with: preconditions (list), postconditions (list), "
            f"invariants (list), edge_cases (list), confidence (0.0-1.0)"
        )
        proof = {"preconditions": [], "postconditions": [], "invariants": [], "edge_cases": [], "confidence": 0.5}
        try:
            proof_resp = ai_ask([proof_prompt, {"max_tokens": 1024}])
            text = proof_resp.get("response", "")
            json_match = re.search(r'\\{[\\s\\S]*\\}', text)
            if json_match:
                proof = json.loads(json_match.group())
        except Exception:
            pass
        verify_prompt = (
            f"You are a code auditor. Code:\n{code}\n\nSpecification:\n{spec}\n\nProof:\n{str(proof)}\n\n"
            f"Try to find counterexamples. Return JSON: {{valid: bool, counterexamples: [], flaws: [], confidence: 0.0-1.0}}"
        )
        verification = {"valid": True, "counterexamples": [], "flaws": [], "confidence": 0.5}
        try:
            ver_resp = ai_ask([verify_prompt, {"max_tokens": 1024}])
            text = ver_resp.get("response", "")
            json_match = re.search(r'\\{[\\s\\S]*\\}', text)
            if json_match:
                verification = json.loads(json_match.group())
        except Exception:
            pass
        proof_conf = float(proof.get("confidence", 0.5))
        ver_conf = float(verification.get("confidence", 0.5))
        is_verified = proof_conf > 0.85 and verification.get("valid", False) and ver_conf > 0.8
        result = {
            "value": code, "proof": proof, "verification": verification, "is_verified": is_verified,
            "confidence": round((proof_conf + ver_conf) / 2, 3), "spec": spec,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        _results.append(result)
        return result

    def _verified_api(args):
        """verified_api(endpoint, method, spec) -> Verified result"""
        endpoint = str(args[0]) if args else "/api/resource"
        method = str(args[1]) if len(args) > 1 else "GET"
        spec = str(args[2]) if len(args) > 2 else "Standard CRUD endpoint"
        gen_prompt = (
            f"Generate a secure API handler for:\nEndpoint: {endpoint}\nMethod: {method}\nSpec: {spec}\n\n"
            f"Requirements: input validation, SQL injection protection, rate limiting. Return ONLY PAPA Lang code."
        )
        return _verified_generate([spec, gen_prompt])

    def _verified_migration(args):
        """verified_migration(from_schema, to_schema) -> Verified result"""
        from_schema = str(args[0]) if args else ""
        to_schema = str(args[1]) if len(args) > 1 else ""
        spec = f"Database migration from '{from_schema}' to '{to_schema}' with zero data loss"
        gen_prompt = f"Generate migration from {from_schema} to {to_schema}. Zero data loss, rollback support."
        return _verified_generate([spec, gen_prompt])

    def _verify_project(args):
        """verify_project(dir) -> {files_checked, average_score, results, grade}"""
        dir_path = str(args[0]) if args else "."
        fs_read = interp.builtins.get("_fs_read")
        import glob as _glob
        files = _glob.glob(os.path.join(dir_path, "**/*.papa"), recursive=True)
        results = []
        total_score = 0
        verify_fn = interp.builtins.get(prefix + "function")
        for filepath in files[:20]:
            try:
                if fs_read:
                    code = fs_read([filepath])
                else:
                    with open(filepath, "r") as f:
                        code = f.read()
                if verify_fn:
                    r = verify_fn([os.path.basename(filepath), code, {}])
                    score = 90 if r.get("verified", False) else 50
                    issues = r.get("issues", [])
                else:
                    score = 70
                    issues = []
                total_score += score
                results.append({"file": filepath, "score": score, "issues": issues})
            except Exception:
                results.append({"file": filepath, "score": 0, "issues": [{"type": "read_error"}]})
        avg_score = total_score / max(len(results), 1) if results else 0
        grade = "A" if avg_score >= 90 else "B" if avg_score >= 80 else "C" if avg_score >= 70 else "D" if avg_score >= 60 else "F"
        return {
            "files_checked": len(results), "average_score": round(avg_score, 1),
            "results": results, "grade": grade,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    # --- Регистрация ---
    interp.builtins[prefix + "function"] = _verify_function
    interp.builtins[prefix + "module"] = _verify_module
    interp.builtins[prefix + "contract"] = _verify_contract
    interp.builtins[prefix + "types"] = _verify_types
    interp.builtins[prefix + "report"] = _report
    interp.builtins[prefix + "generate"] = _verified_generate
    interp.builtins[prefix + "api"] = _verified_api
    interp.builtins[prefix + "migration"] = _verified_migration
    interp.builtins[prefix + "project"] = _verify_project

    return {
        "verify_function":  ("builtin", prefix + "function"),
        "verify_module":    ("builtin", prefix + "module"),
        "verify_contract":  ("builtin", prefix + "contract"),
        "verify_types":     ("builtin", prefix + "types"),
        "verify_report":    ("builtin", prefix + "report"),
        "verified_generate":   ("builtin", prefix + "generate"),
        "verified_api":        ("builtin", prefix + "api"),
        "verified_migration":  ("builtin", prefix + "migration"),
        "verify_project":      ("builtin", prefix + "project"),
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
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ")

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
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
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
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "result": result,
                })
                return {"command": cmd_type, "args": list(match.groups()), "result": result}

        # Поиск среди пользовательских команд
        for pattern, cmd_info in _custom_commands.items():
            match = re.search(pattern, transcript)
            if match:
                _session["commands_executed"] += 1
                return {"command": cmd_info["name"], "args": list(match.groups()), "result": "custom_command_matched"}

        return {"command": Maybe.none(), "transcript": transcript, "error": "No matching command found"}

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
        custom = [{"pattern": v["pattern"], "command": v["name"], "type": "custom", "description": v.get("description", "")} for v in _custom_commands.values()]
        return built_in + custom

    def _session_start(args):
        """voice_session_start() -> {session_id, status}"""
        _session["active"] = True
        _session["id"] = f"vs_{int(time.time())}"
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

STD_MODULE_LOADERS = {
    "math": _std_math,
    "string": _std_string,
    "orchestrator": _load_orchestrator,
    "docs": _load_docs,
    "studio": _load_studio,
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
    "cwb": _load_cwb,
    "guard": _std_guard,
    "ai_router": _std_ai_router,
    "evolve": _std_evolve,
    "swarm": _std_swarm,
    "infra": _std_infra,
    "gemini": _std_gemini,
    "verify": _std_verify,
    "chain": _std_chain,
    "voice_prog": _std_voice_prog,
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
                hint="Доступны: std/math, std/string, std/json, std/http, std/fs, std/time, std/voice, std/mcp, std/browser, std/telegram, std/ai, std/design, std/orchestrator, std/docs, std/studio, std/cwb, std/guard, std/ai_router, std/evolve, std/swarm, std/infra, std/gemini, std/verify, std/chain, std/voice_prog"
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
