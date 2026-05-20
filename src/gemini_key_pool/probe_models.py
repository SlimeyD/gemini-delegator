#!/usr/bin/env python3
"""
One-shot empirical probe: which models are actually accessible on the free tier
across our existing keys? Used to ground model-capabilities.yaml in reality.

For each of (BAMBOO_1, RATEMYFLAT_1, ENSPIRAL_1):
  - GET /v1beta/models — list every model the key can see.
  - For each candidate model, send a 1-token generateContent ping.
  - Record: HTTP status, error code, latency, response excerpt.

Writes a markdown report and prints a summary table.

Cost: ~3 keys × ~7 models = ~21 free-tier requests. Negligible.
"""
from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    sys.exit("Run with the project venv: ~/Code/ai-orchestration/scripts/.venv/bin/python3")

import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

KEYS_TO_PROBE = [
    ("BAMBOO_1",     os.environ.get("BAMBOO_GEMINI_API_KEY_1", "")),
    ("RATEMYFLAT_1", os.environ.get("RATEMYFLAT_GEMINI_API_KEY_1", "")),
    ("ENSPIRAL_1",   os.environ.get("ENSPIRAL_GEMINI_API_KEY_1", "")),
]

CANDIDATE_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-preview",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-3.1-pro-preview",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemma-3-27b",
    "gemma-3-27b-it",
    "gemma-4-31b",
    "gemma-4-31b-it",
]

BASE = "https://generativelanguage.googleapis.com/v1beta"
TINY_PROMPT = {"contents": [{"parts": [{"text": "Say 'ok'"}]}]}


@dataclass
class ProbeResult:
    key_label: str
    model: str
    status: int
    latency_ms: int
    error_code: str = ""
    body_excerpt: str = ""


def http_request(url: str, key: str, body: dict | None, timeout: int = 15) -> tuple[int, str, int]:
    """Returns (status, body_text, latency_ms). Doesn't raise on HTTP errors."""
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if body else "GET")
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode()
            return resp.status, text, int((time.monotonic() - start) * 1000)
    except urllib.error.HTTPError as e:
        text = e.read().decode() if e.fp else str(e)
        return e.code, text, int((time.monotonic() - start) * 1000)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return 0, f"NETWORK: {e}", int((time.monotonic() - start) * 1000)


def list_models(key_label: str, key: str) -> dict:
    """Returns {model_name: short_description} of every model this key can list."""
    if not key:
        return {"_error": f"{key_label} key not set in env"}
    status, text, _ = http_request(f"{BASE}/models", key, None)
    if status != 200:
        return {"_error": f"HTTP {status}: {text[:200]}"}
    try:
        models = json.loads(text).get("models", [])
        return {m["name"].split("/")[-1]: m.get("displayName", "") for m in models}
    except (json.JSONDecodeError, KeyError) as e:
        return {"_error": f"parse: {e}"}


def probe_model(key_label: str, key: str, model: str) -> ProbeResult:
    url = f"{BASE}/models/{model}:generateContent"
    status, body, latency = http_request(url, key, TINY_PROMPT)
    error_code = ""
    body_excerpt = ""
    if status != 200:
        try:
            parsed = json.loads(body)
            error = parsed.get("error", {})
            error_code = f"{error.get('status', '')}:{error.get('code', status)}"
            body_excerpt = (error.get("message", "") or body)[:160]
        except json.JSONDecodeError:
            body_excerpt = body[:160]
    else:
        try:
            parsed = json.loads(body)
            text = parsed["candidates"][0]["content"]["parts"][0].get("text", "")
            body_excerpt = text[:60].replace("\n", " ")
        except (KeyError, IndexError):
            body_excerpt = body[:80]
    return ProbeResult(key_label, model, status, latency, error_code, body_excerpt)


def status_glyph(r: ProbeResult) -> str:
    if r.status == 200:
        return "✅ free"
    if r.status == 429:
        return "🔶 quota"
    if r.status == 404:
        return "❌ 404"
    if r.status == 403:
        return "🔒 403"
    if r.status == 400 and "FAILED_PRECONDITION" in r.error_code:
        return "💰 paid"
    if r.status == 0:
        return "📡 net"
    return f"⚠️  {r.status}"


def main() -> int:
    report_path = Path("/tmp/probe-results.md")
    lines: list[str] = [f"# Gemini model probe — {time.strftime('%Y-%m-%d %H:%M:%S')}\n"]

    # Phase 1: list models per key
    print("== Phase 1: listing models per key ==", flush=True)
    available_per_key: dict[str, dict] = {}
    for label, key in KEYS_TO_PROBE:
        print(f"  GET /v1beta/models for {label}...", end=" ", flush=True)
        result = list_models(label, key)
        available_per_key[label] = result
        if "_error" in result:
            print(f"ERROR {result['_error'][:100]}")
        else:
            print(f"{len(result)} models")

    lines.append("## Phase 1: Models listed per key\n")
    all_listed = set()
    for label, models in available_per_key.items():
        if "_error" in models:
            lines.append(f"### {label}\n\n_Error_: `{models['_error']}`\n")
            continue
        all_listed.update(models.keys())
        lines.append(f"### {label} ({len(models)} models)\n")
        lines.append("<details><summary>full list</summary>\n\n```")
        for name in sorted(models.keys()):
            lines.append(name)
        lines.append("```\n</details>\n")

    # Phase 2: generate probes against candidate models, in parallel across keys
    print("\n== Phase 2: tiny generate probes ==", flush=True)
    probe_jobs = []
    for label, key in KEYS_TO_PROBE:
        if not key:
            continue
        for model in CANDIDATE_MODELS:
            probe_jobs.append((label, key, model))

    results: list[ProbeResult] = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        # Group by key so each key probes its models serially (free-tier RPM friendly),
        # but the 3 keys probe in parallel.
        def probe_key_serial(label: str, key: str):
            out: list[ProbeResult] = []
            for model in CANDIDATE_MODELS:
                r = probe_model(label, key, model)
                out.append(r)
                print(f"  {label:14} {model:36} → {status_glyph(r):10} ({r.latency_ms}ms)", flush=True)
                # Free tier = 5 RPM per project. Sleep 12s between probes so
                # quota-driven 429s don't get confused with "model unavailable".
                time.sleep(12.0)
            return out

        futures = [pool.submit(probe_key_serial, label, key) for label, key in KEYS_TO_PROBE if key]
        for f in as_completed(futures):
            results.extend(f.result())

    # Phase 3: render table
    lines.append("\n## Phase 2: Probe results\n")
    lines.append("| Model | " + " | ".join(label for label, _ in KEYS_TO_PROBE) + " |")
    lines.append("|" + "---|" * (len(KEYS_TO_PROBE) + 1))
    by_model: dict[str, dict[str, ProbeResult]] = {}
    for r in results:
        by_model.setdefault(r.model, {})[r.key_label] = r
    for model in CANDIDATE_MODELS:
        row = [model]
        for label, _ in KEYS_TO_PROBE:
            r = by_model.get(model, {}).get(label)
            if r is None:
                row.append("—")
            else:
                row.append(status_glyph(r))
        lines.append("| " + " | ".join(row) + " |")

    # Detailed errors for anything non-200
    lines.append("\n## Notable errors\n")
    seen_errors: set[str] = set()
    for r in results:
        if r.status == 200:
            continue
        sig = f"{r.model}|{r.error_code}"
        if sig in seen_errors:
            continue
        seen_errors.add(sig)
        lines.append(f"- **{r.model}** ({r.error_code or r.status}): `{r.body_excerpt}`")

    report_path.write_text("\n".join(lines) + "\n")
    print(f"\nReport: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
