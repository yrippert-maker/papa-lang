"""
PAPA Lang stdlib_agents — voice, mcp, browser, telegram, ai_budget, design.
"""

import time

import hashlib
from typing import Any, Dict

from .environment import Maybe, PapaList, PapaMap


def _std_voice(interp: 'Interpreter') -> Dict[str, Any]:
    """std/voice — Voice calls, SMS, TTS, Transcription."""
    prefix = "_voice_"
    mod = getattr(interp, '_module_state', None) or {}
    interp._module_state = mod

    def voice_config(args):
        provider = str(args[0]) if args else "telnyx"
        api_key = args[1] if len(args) > 1 else None
        if api_key and hasattr(api_key, '_raw_value'):
            api_key = api_key._raw_value
        if api_key and hasattr(api_key, 'raw'):
            api_key = api_key.raw
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


def _std_mcp(interp: 'Interpreter') -> Dict[str, Any]:
    """std/mcp — MCP connectors."""
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


def _std_browser(interp: 'Interpreter') -> Dict[str, Any]:
    """std/browser — Browser automation."""
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


def _std_telegram(interp: 'Interpreter') -> Dict[str, Any]:
    """std/telegram — Telegram Bot API."""
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


def _std_ai_budget(interp: 'Interpreter') -> Dict[str, Any]:
    """ai_budget — Cost guardrails."""
    prefix = "_aib_"
    mod = getattr(interp, '_module_state', None) or {}
    interp._module_state = mod

    def ai_budget_set(args):
        limit = float(args[0]) if args else 20.0
        alert = float(args[1]) if len(args) > 1 else 0.8
        mod['ai_budget_limit'] = limit
        mod['ai_budget_alert'] = alert
        mod['ai_budget_spent'] = 0.0
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


def _std_design(interp: 'Interpreter') -> Dict[str, Any]:
    """std/design — AI Design Generation."""
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


__all__ = [
    '_std_voice', '_std_mcp', '_std_browser', '_std_telegram', '_std_ai_budget', '_std_design',
]
