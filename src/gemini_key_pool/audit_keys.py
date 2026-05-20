#!/usr/bin/env python3
"""
Audit every Gemini API key in your .env against the live Generative Language API.

Pings each key with a tiny generateContent call to gemini-3.5-flash and
records: alive/blocked/exhausted/expired/error, plus latency. Writes a
markdown report to logs/key-audit-YYYY-MM-DD.md and prints a checklist of
keys that need action before the June 19, 2026 deadline (when unrestricted
keys stop working — see https://ai.google.dev/gemini-api/docs/api-key).

Recognised env var patterns (any one works):
- GEMINI_API_KEY_1 ... GEMINI_API_KEY_N
- <PREFIX>_GEMINI_API_KEY_N (e.g. BAMBOO_GEMINI_API_KEY_3, PROJ1_GEMINI_API_KEY_1)
- GEMINI_KEY_PROJECT_N (legacy)

Run weekly until June 19 to catch keys that get auto-blocked.

Cost: 1 free-tier request per key. Negligible.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    sys.exit("Install python-dotenv: pip install python-dotenv")

# Try to find a .env file: package layout first, then CWD.
_HERE = Path(__file__).resolve()
ROOT = _HERE.parent.parent.parent  # src/gemini_key_pool/audit_keys.py → repo root
for _candidate in (ROOT / ".env", Path.cwd() / ".env"):
    if _candidate.exists():
        load_dotenv(_candidate)
        ROOT = _candidate.parent
        break

BASE = "https://generativelanguage.googleapis.com/v1beta"
TEST_MODEL = "gemini-3.5-flash"  # free-tier eligible, fast
TINY_PROMPT = {"contents": [{"parts": [{"text": "ok"}]}]}
DEADLINE_NOTE = "https://ai.google.dev/gemini-api/docs/api-key#secure-unrestricted-api-keys"


@dataclass
class KeyStatus:
    label: str         # e.g. "BAMBOO_GEMINI_API_KEY_3"
    project: str       # e.g. "bamboo"
    key_present: bool
    http_status: int = 0
    latency_ms: int = 0
    state: str = ""    # "alive" | "blocked" | "exhausted" | "missing" | "error" | "404"
    note: str = ""


def enumerate_keys() -> list[tuple[str, str, str]]:
    """Return [(label, project, key_value), ...] for every Gemini-shaped env var.

    Recognised forms:
      GEMINI_API_KEY_N            → project = "default"
      <PREFIX>_GEMINI_API_KEY_N   → project = "<prefix>" (lowercased)
      GEMINI_KEY_PROJECT_N        → project = "default" (legacy)
    """
    keys: list[tuple[str, str, str]] = []
    pattern_prefixed = re.compile(r"^([A-Z][A-Z0-9]*)_GEMINI_API_KEY_(\d+)$")
    pattern_plain    = re.compile(r"^GEMINI_API_KEY_(\d+)$")
    pattern_legacy   = re.compile(r"^GEMINI_KEY_PROJECT_(\d+)$")
    for var_name in sorted(os.environ.keys()):
        val = os.environ.get(var_name, "")
        if not val or not val.startswith("AIza"):
            # Skip empty vars and ones that don't look like Gemini keys.
            continue
        if pattern_plain.match(var_name) or pattern_legacy.match(var_name):
            keys.append((var_name, "default", val))
            continue
        m = pattern_prefixed.match(var_name)
        if m:
            keys.append((var_name, m.group(1).lower(), val))
    return keys


def probe(label: str, project: str, key: str) -> KeyStatus:
    status = KeyStatus(label=label, project=project, key_present=bool(key))
    if not key:
        status.state = "missing"
        status.note = f"Env var {label} is empty"
        return status

    url = f"{BASE}/models/{TEST_MODEL}:generateContent"
    req = urllib.request.Request(
        url,
        data=json.dumps(TINY_PROMPT).encode(),
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        method="POST",
    )
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
            status.http_status = resp.status
            status.latency_ms = int((time.monotonic() - start) * 1000)
            status.state = "alive"
            status.note = "200 OK — key works against Generative Language API"
            return status
    except urllib.error.HTTPError as e:
        status.http_status = e.code
        status.latency_ms = int((time.monotonic() - start) * 1000)
        body = ""
        try:
            body = e.read().decode()
            err = json.loads(body).get("error", {})
            err_status = err.get("status", "")
            err_msg = err.get("message", "")[:160]
        except (json.JSONDecodeError, AttributeError):
            err_status = ""
            err_msg = body[:160]

        if e.code in (401, 403):
            status.state = "blocked"
            status.note = f"{e.code} {err_status} — key may be blocked/restricted. {err_msg}"
        elif e.code == 429:
            status.state = "exhausted"
            status.note = f"429 {err_status} — quota exhausted (likely free-tier RPM/RPD). {err_msg}"
        elif e.code == 404:
            status.state = "404"
            status.note = f"404 — {TEST_MODEL} not available to this key. {err_msg}"
        elif e.code == 400 and "expired" in err_msg.lower():
            status.state = "expired"
            status.note = f"400 — key expired, needs regeneration. {err_msg}"
        else:
            status.state = "error"
            status.note = f"{e.code} {err_status}: {err_msg}"
        return status
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        status.latency_ms = int((time.monotonic() - start) * 1000)
        status.state = "error"
        status.note = f"network: {e}"
        return status


def render_report(statuses: list[KeyStatus]) -> str:
    lines: list[str] = []
    today = time.strftime("%Y-%m-%d")
    lines.append(f"# Gemini API key audit — {today}\n")
    lines.append(f"Probed {len(statuses)} keys against `{TEST_MODEL}` "
                 f"({BASE}).\n")

    # Summary counts
    by_state: dict[str, int] = {}
    for s in statuses:
        by_state[s.state] = by_state.get(s.state, 0) + 1
    lines.append("## Summary\n")
    for state in ("alive", "exhausted", "blocked", "expired", "404", "error", "missing"):
        if state in by_state:
            lines.append(f"- **{state}**: {by_state[state]}")
    lines.append("")

    # Deadline reminder
    lines.append("## ⚠️ June 19, 2026 deadline\n")
    lines.append("Unrestricted keys stop working on June 19, 2026. "
                 f"See {DEADLINE_NOTE}.\n")
    lines.append("This script cannot determine restriction status via the API. "
                 "Manually verify in AI Studio → API Keys that every alive key "
                 "shows 'Restrict to Gemini API' applied, or restrict in Cloud "
                 "Console credentials page.\n")

    # Per-project grouping
    lines.append("## Per-project status\n")
    by_project: dict[str, list[KeyStatus]] = {}
    for s in statuses:
        by_project.setdefault(s.project, []).append(s)
    for project in sorted(by_project):
        project_keys = by_project[project]
        alive_count = sum(1 for k in project_keys if k.state == "alive")
        lines.append(f"### `{project}` ({alive_count}/{len(project_keys)} alive)\n")
        lines.append("| Key | State | HTTP | Latency | Note |")
        lines.append("|---|---|---|---|---|")
        for s in project_keys:
            note = s.note.replace("|", "\\|")
            lines.append(f"| `{s.label}` | {s.state} | {s.http_status} | "
                         f"{s.latency_ms}ms | {note} |")
        lines.append("")

    # Action checklist
    lines.append("## Action checklist\n")
    actions: list[str] = []
    for s in statuses:
        if s.state == "blocked":
            actions.append(f"- [ ] **{s.label}** is blocked — regenerate in AI "
                           f"Studio or restrict to Generative Language API")
        elif s.state == "expired":
            actions.append(f"- [ ] **{s.label}** is **EXPIRED** — regenerate in "
                           f"[AI Studio](https://aistudio.google.com/app/apikey) and update `.env`")
        elif s.state == "missing":
            actions.append(f"- [ ] **{s.label}** is empty in `.env` — set it or remove the line")
        elif s.state == "404":
            actions.append(f"- [ ] **{s.label}** can't see `{TEST_MODEL}` — "
                           f"project may need the Generative Language API enabled")
    if actions:
        lines.extend(actions)
    else:
        lines.append("_No blockers detected. Still verify restriction status manually before June 19._")

    return "\n".join(lines) + "\n"


def main() -> int:
    keys = enumerate_keys()
    if not keys:
        print("No *_GEMINI_API_KEY_N variables found in .env", file=sys.stderr)
        return 1

    print(f"Probing {len(keys)} keys against {TEST_MODEL}...\n", flush=True)
    statuses: list[KeyStatus] = []
    # Parallel across keys (different projects have independent quotas)
    with ThreadPoolExecutor(max_workers=8) as pool:
        for s in pool.map(lambda kv: probe(*kv), keys):
            statuses.append(s)
            glyph = {
                "alive": "✅", "exhausted": "🔶", "blocked": "🔒",
                "expired": "⏰", "404": "❌", "error": "⚠️ ", "missing": "—",
            }.get(s.state, "?")
            print(f"  {glyph} {s.label:30} {s.state:9} {s.http_status or '-':>3} "
                  f"({s.latency_ms}ms)", flush=True)

    statuses.sort(key=lambda s: (s.project, s.label))

    logs_dir = ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)
    report_path = logs_dir / f"key-audit-{time.strftime('%Y-%m-%d')}.md"
    report_path.write_text(render_report(statuses))
    print(f"\nReport: {report_path}")

    # Exit non-zero if any key needs urgent attention
    needs_action = sum(1 for s in statuses if s.state in ("blocked", "expired", "missing", "404"))
    if needs_action:
        print(f"\n⚠️  {needs_action} key(s) need action — see report.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
