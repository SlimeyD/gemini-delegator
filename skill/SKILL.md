---
name: gemini-delegator
description: Delegate work to Gemini agents to save tokens on your orchestrator model (Claude, GPT, etc.) and gain parallel throughput from a pool of free-tier Gemini keys. Gemini agents do code generation, structured extraction, data analysis with a Python sandbox, web research with Google Search grounding, and image work. Use this skill whenever you're doing medium-to-high complexity work — writing code, summarizing, reviewing, analyzing, extracting JSON, charting, web research, prototyping. Also use for orchestration patterns: council of experts, parallel review, plan execution. If a task has clear inputs and success criteria and doesn't need conversation context, delegate it.
---

# Gemini Delegator

You have a workforce of Gemini agents available via shell commands. Your job is to **orchestrate** — break work into delegable pieces, dispatch them, validate the results, and synthesize for the user.

This isn't something you do only when asked. Whenever you recognize work that Gemini handles well, route it there automatically. The user benefits from faster results and you preserve your context for the reasoning that matters.

## Free-tier ground truth (verified 2026-05-20)

Limits are **per Google Cloud project**, not per key. Each AI Studio account allows up to **8 keys per project** (10 projects per account by docs, but per-project key creation caps at 8). The pool's throughput ceiling = (number of projects) × (per-model RPM).

### Models you can route to safely

| Model | RPM | TPM | RPD | Best for |
|---|---|---|---|---|
| `gemini-3.5-flash` | 5 | 250K | 20 | Default for writing, code-gen, anything needing thinking |
| `gemini-3.1-flash-lite` | 15 | 250K | **500** | The workhorse — 500 RPD is the best free quota |
| `gemini-3-flash` | 5 | 250K | 20 | Backup when 3.5 exhausted |
| `gemini-2.5-flash` | 5 | 250K | 20 | **Required for Search grounding** (paid on Gemini 3.x) |
| `gemini-2.5-flash-lite` | 10 | 250K | 20 | Cheapest non-Gemma free flash |
| `gemma-4-31b` | 15 | **Unlimited** | 1500 | **Batch + structured extraction** (unlimited TPM) |
| `gemini-embedding-2` | 100 | 30K | 1K | Embeddings |

### Paid-only — DO NOT route here without explicit user authorisation

These return `429 RESOURCE_EXHAUSTED` on every free-tier key:

- **Text:** `gemini-3.1-pro`, `gemini-3-pro`, `gemini-2.5-pro` (despite docs claiming free tier — dashboard reality is 0/0/0)
- **Image:** Nano Banana family (`gemini-2.5/3-flash-image`, `gemini-3-pro-image`), Imagen 4
- **Video:** Veo 2 / 3 / 3.1
- **Music:** Lyria 3
- **Agentic:** Computer Use Preview, Deep Research

## Should I delegate this?

```
Is this task...
  ├─ Independent (doesn't need conversation context)? → DELEGATE fully
  ├─ Well-defined (clear input, clear success criteria)? → DELEGATE fully
  ├─ Writing — code, components, copy, prototypes? → DELEGATE
  ├─ Extraction — pull JSON from text/docs? → DELEGATE to Gemma 4 (unlimited TPM)
  ├─ Research — web facts with citations? → DELEGATE to 2.5 Flash + search grounding
  ├─ Batch processing — many items, same op? → DELEGATE in parallel
  ├─ Council of experts / parallel review? → DELEGATE
  ├─ Interactive but with research component? → DELEGATE research, KEEP conversation
  └─ Needs your orchestrator's tools or live credentials? → KEEP
```

## How to delegate

### Single task

```bash
python3 -m gemini_key_pool.gemini_agent \
  --task "Your detailed prompt here" \
  --output /tmp/result.md
```

### Useful flags

| Flag | Purpose | Example |
|------|---------|---------|
| `--quality draft\|standard\|production\|research` | Thinking depth | `--quality production` |
| `--context-file path` | Feed additional text context | `--context-file /tmp/summary.md` |
| `--image-file path` | Image understanding input | `--image-file screenshot.png` |
| `--image-output path` | Image generation output (paid) | `--image-output /tmp/logo.png` |
| `--enable-tools` | Enable Search + code execution | Research tasks, data analysis |
| `--json` | Output result as structured JSON | Machine-parseable |
| `--capture-thinking` | Return model's reasoning trace | Debugging |

## Tool-call accounting (this matters for free tier)

Built-in tools and function calling cost different numbers of API requests. Get this wrong and an "agentic" delegation burns through the 5-RPM ceiling in seconds.

| Pattern | Requests per turn | Notes |
|---|---|---|
| Plain text generation | 1 | Baseline |
| Built-in tools (Search, Map, Code Exec, URL Context) | **1** | Model iterates internally, returns final answer |
| Function calling (custom tools) | **2 per round** | Model proposes → execute → return → final response |
| Multi-turn agentic loops | **2 × N rounds** | 5-step workflow = 10 requests = burns 5 RPM in seconds |
| Search query inside grounded request | 1 (model side) + N billable searches | Search grounding has separate 1.5K-RPD bucket (free on 2.x only) |

**Implication:** multi-step agentic workflows on free tier are structurally constrained. Either keep multi-step automation in your orchestrator, batch tool calls aggressively, or use a paid key.

Single-shot tools are way cheaper than they look. `extract structured JSON from a search query with code-verified output` is **one request**.

## Tool combinability

Gemini 3.x supports combining ALL of these in ONE request: Structured Outputs + Google Search grounding + URL Context + Code Execution + File Search + Function Calling.

This unlocks single-request workflows that previously needed 3-4 calls.

## Crafting good delegation prompts

Gemini agents have no conversation context. Everything they need must be in the prompt.

**Bad:**
```
"Review the code"
```

**Good:**
```
"Review src/auth/login.py for:
1. Security vulnerabilities (injection, XSS, auth bypass)
2. Error handling completeness
3. Edge cases not covered

Here is the file content:
[paste or use --context-file]

Output format:
- Issue description with line numbers
- Severity (critical/high/medium/low)
- Suggested fix"
```

## Validating Gemini output

This is non-negotiable. Gemini agents are fast but can hallucinate — especially on:
- File paths and directory structures (may invent paths that don't exist)
- Feature descriptions (may describe features the product doesn't have)
- Specific code details (verify against actual source)

Always read the output and cross-check key claims before presenting to the user. For code suggestions, verify they compile/run. For factual claims, spot-check against the source material.

## Orchestration patterns

### Parallel-Aggregate (most common)

Multiple agents analyze the same input from different angles, you synthesize.

```
User: "Review this codebase thoroughly"

Dispatch in parallel:
  Agent 1: "Review src/auth/ for security vulnerabilities..." → /tmp/security.md
  Agent 2: "Review src/auth/ for performance bottlenecks..." → /tmp/perf.md
  Agent 3: "Review src/auth/ for code quality..." → /tmp/quality.md

You synthesize: Read all three, prioritize findings, present unified review.
```

### Council of Experts

A specialized form of Parallel-Aggregate where each agent adopts an expert persona.

```
Dispatch 5-7 domain experts in parallel:
  UX, Visual Design, Performance, SEO, Accessibility, Copywriting

Each writes findings to /tmp/expert-{domain}.md
You consolidate by severity, cross-referencing where experts agree.
```

### Batch Processing

Same operation across many items. **Use Gemma 4 31B for batch extraction** — unlimited TPM means you can stuff giant prompts in.

## Key audit (June 19, 2026 deadline)

**Unrestricted keys stop working June 19, 2026.** Every key in `.env` must be restricted to "Generative Language API" in AI Studio before then. The package ships an audit tool:

```bash
python3 -m gemini_key_pool.audit_keys
```

Run weekly. Writes a report to `logs/key-audit-YYYY-MM-DD.md` with per-project status and a checklist for keys that need action.

## What Gemini agents cannot do

- Access your conversation history (everything must be in the prompt)
- Interact with the user mid-task
- Maintain state between separate calls
- Install custom Python packages (only ~25 pre-installed: numpy, pandas, scikit-learn, scipy, opencv, tensorflow, geopandas, matplotlib, ...)
- Code execution sandbox has a 30-second timeout

## Diagnosing a 429

1. **Was the model paid-only?** Re-read the table above.
2. **Was it the model's RPM (5 or 15)?** Stagger dispatches with 12-second gaps.
3. **Was it the model's RPD (20 or 500)?** Resets at midnight Pacific.
4. **Was it a tool sub-quota?** Search grounding has separate 1.5K-RPD on Gemini 2.x (0 on 3.x). Map grounding 500 RPD. Tools have their own buckets.
5. **Was it function-calling overhead?** Multi-turn workflows multiply requests — see tool accounting table.
