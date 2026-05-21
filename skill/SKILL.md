---
name: gemini-delegator
description: Delegate work to Gemini agents to save tokens on your orchestrator model (Claude, GPT, etc.) and gain parallel throughput from a pool of free-tier Gemini keys. Gemini agents do code generation, structured extraction, data analysis with a Python sandbox, web research with Google Search grounding, and image work. Use this skill whenever you're doing medium-to-high complexity work — writing code, summarizing, reviewing, analyzing, extracting JSON, charting, web research, prototyping. Also use for orchestration patterns: council of experts, parallel review, plan execution. If a task has clear inputs and success criteria and doesn't need conversation context, delegate it.
---

# Gemini Delegator

You orchestrate. Route work to Gemini whenever a task is independent, well-defined, and doesn't need conversation context — Gemini gets faster turnaround and parallel throughput, and you preserve your own context for synthesis and judgment. This is the default posture, not something to do only when asked.

## Should I delegate this?

```
Is this task...
  ├─ Independent + well-defined (clear input, clear success)? → DELEGATE
  ├─ Writing — code, components, copy, prototypes?            → DELEGATE
  ├─ Extraction — pull JSON from text/docs?                   → DELEGATE to Gemma 4 (unlimited TPM)
  ├─ Research with citations?                                 → DELEGATE to 2.5 Flash + --enable-tools
  ├─ Batch — many items, same operation?                      → DELEGATE in parallel
  ├─ Multi-perspective review / council-of-experts?           → DELEGATE
  └─ Needs your orchestrator's tools or live credentials?     → KEEP
```

## How to delegate

```bash
python3 -m gemini_key_pool.gemini_agent \
  --task "Your detailed prompt here" \
  --output /tmp/result.md
```

### Picking a model — quick rules

- **Default code/writing workhorse:** `gemini-3.5-flash` — 20 RPD per project, good thinking depth.
- **Batch + structured extraction:** `gemma-4-31b` (unlimited TPM, 1500 RPD). Cheap to stuff giant prompts in.
- **Research with citations:** `gemini-2.5-flash` + `--enable-tools` (Search grounding is paid on Gemini 3.x — 2.5 is the free path).
- **High volume / small tasks:** `gemini-3.1-flash-lite` — 500 RPD is the best free quota.
- **Paid models** (Pro / image / video / agentic): not callable from a free-tier key. Use a paid Google Cloud key if you need them.
- Full quota numbers and 429 diagnosis: [references/quotas.md](references/quotas.md).

### Useful flags

| Flag | Purpose | Example |
|------|---------|---------|
| `--task-file path` | Read the prompt from a file (better than inline `--task` for multi-line) | `--task-file /tmp/task.md` |
| `--quality draft\|standard\|production\|research` | Thinking depth | `--quality production` |
| `--context-file path` | Feed additional text context. Repeat for multiple files. | `--context-file a.md --context-file b.md` |
| `--context-glob 'pattern'` | Glob-expanded context files (repeatable) | `--context-glob 'docs/**/*.md'` |
| `--image-file path` | Image understanding input | `--image-file screenshot.png` |
| `--image-output path` | Image generation output (paid) | `--image-output /tmp/logo.png` |
| `--enable-tools` | Enable Search + code execution | Research tasks, data analysis |
| `--json` | Output result as structured JSON | Machine-parseable |
| `--capture-thinking` | Return model's reasoning trace | Debugging |

## Stack-aware delegation

Before writing the task prompt, think about what context Gemini will need —
Gemini is stateless and has no access to your project, conventions, or
domain-specific rules.

1. **Identify which existing rule files apply.** If you have project-level
   instructions for your orchestrator (e.g. `CLAUDE.md`, `GEMINI.md`,
   `AGENTS.md`), gather the relevant excerpts.
2. **Identify which existing skills encode the relevant patterns.** For
   example, React/Next.js skills, Postgres skills, brand-voice skills. If
   you have skill `SKILL.md` files locally, include them.
3. **Pass everything via repeated `--context-file`** (or `--context-glob`).
   The agent aggregates them into a single context block with
   `## Context: <path>` headers:

   ```bash
   python3 -m gemini_key_pool.gemini_agent \
     --task-file /tmp/my-task.md \
     --context-file path/to/CLAUDE.md \
     --context-file path/to/relevant-skill/SKILL.md \
     --context-file path/to/code-file.tsx \
     --output /tmp/out.md
   ```
4. **Write a sharp task prompt** that points to the context and names the
   desired output.

**Don't curate "the relevant subset" of skill content.** Gemini's TPM is
generous within a single request (250K on flash models, unlimited on Gemma).
Dump the relevant context in full; spend effort on making the **task prompt**
sharp instead.

## Shell escaping when prompts get long

Inlining a multi-paragraph `--task` string into bash is fragile (quote
breakage, backtick interpolation, dollar-sign expansion). Prefer:

```bash
python3 -m gemini_key_pool.gemini_agent \
  --task-file /tmp/my-task.md \
  --context-file /tmp/ctx.md \
  --output /tmp/out.md
```

If you're piping or composing on the fly, this also works:

```bash
python3 -m gemini_key_pool.gemini_agent \
  --task "$(cat /tmp/my-task.md)" --context-file /tmp/ctx.md --output /tmp/out.md
```

## Crafting delegation prompts

Gemini agents have no conversation context — everything they need must be in
the prompt or context file. Delegation-specific things to remember:

- **Self-contained.** No references to "the file I just read" or "as we
  discussed." Gemini hasn't read or discussed anything.
- **Name the output format explicitly.** Your orchestrator is going to parse
  the result, so spell out the structure: fenced code blocks with `// FILE:`
  markers, strict JSON shape, markdown with H2/H3 sections, etc.
- **State anti-patterns + project quirks explicitly.** Gemini doesn't know
  them. "Use shadcn/ui primitives in `src/components/ui/`, do not roll a
  new component" beats "follow project conventions."
- **Watch shell escapes.** Use `--task-file` for anything over a few lines.

## Sensitive paths are filtered

`--context-file` and `--context-glob` paths are filtered against a built-in
deny-list of substrings (`.env`, `.ssh`, `.aws`, `credentials`, `secrets`,
`id_rsa`, `id_ed25519`, `private_key`, `service-account`, etc.). A matching
path is refused with a `🛡️` log line. This is a guardrail against
accidentally sending a `.env` to Gemini, not a substitute for thinking about
what you pass in.

## Validating Gemini output

Non-negotiable. Gemini agents are fast but can hallucinate — especially on:

- File paths and directory structures (may invent paths)
- Feature descriptions (may describe features the product doesn't have)
- Code details (verify against actual source)
- **CLI flags** (may invent plausible-looking argparse flags that don't
  exist — grep the source to confirm before relying on them)

Always read the output file and cross-check key claims before presenting to
the user. For code suggestions, verify they compile / run. For factual
claims, spot-check against source material.

## Parallel dispatch

Launch multiple agents in parallel by running them as background processes.
**Throughput ceiling** = (number of GCP projects in your pool) × (per-model
RPM). With a single project's 8 keys, peak is the per-model RPM (5 or 15
depending on the model); with N projects, multiply by N.

## Orchestration patterns

The basics:

- **Parallel-Aggregate**: dispatch 3–5 agents on the same input from
  different angles (security / performance / quality), synthesize their
  reports yourself.
- **Council of Experts**: a specialized Parallel-Aggregate where each agent
  adopts a domain-expert persona (UX, SEO, accessibility, etc.).
- **Sequential Pipeline**: stages where each step's output feeds the next
  (research → analyze → write).
- **Batch Processing**: same operation across many items; use Gemma 4 for
  the unlimited TPM.

For advanced patterns (Hierarchical, Double-Diamond, Handoff Chain,
Structured Debate), see [references/patterns.md](references/patterns.md).

## Key audit (June 19, 2026 deadline)

**Unrestricted keys stop working June 19, 2026.** Every key in `.env` must
be restricted to "Generative Language API" in AI Studio before then. The
package ships an audit tool:

```bash
python3 -m gemini_key_pool.audit_keys
```

Run weekly. Writes a report to `logs/key-audit-YYYY-MM-DD.md` with per-project
status and a checklist for keys that need action.

## What Gemini agents cannot do

- Access your conversation history (everything must be in the prompt)
- Interact with the user mid-task
- Maintain state between separate calls
- Use your orchestrator's tools (Read, Edit, etc.) — pass file contents via
  `--context-file`
- Install custom Python packages (only ~25 pre-installed: numpy, pandas,
  scikit-learn, scipy, opencv, tensorflow, geopandas, matplotlib, ...)
- Code execution sandbox has a 30-second timeout

## References

| File | When to read |
|------|-------------|
| [references/quotas.md](references/quotas.md) | Hit a 429, picking a model under quota pressure, full RPM/TPM/RPD tables |
| [references/cost-mechanics.md](references/cost-mechanics.md) | Tasks involve tools / function-calling; budgeting requests |
| [references/patterns.md](references/patterns.md) | Need patterns beyond the basics (debate, double-diamond, handoff chain) |
| [references/model-capabilities.md](references/model-capabilities.md) | Detailed model specs, fallback chains |
| [references/claude-integration.md](references/claude-integration.md) | Using Claude Code subagents alongside Gemini delegation |
| [references/key-configuration.md](references/key-configuration.md) | API key setup |
