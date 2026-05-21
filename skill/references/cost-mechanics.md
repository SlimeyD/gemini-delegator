# Tool-call accounting and tool combinability

When you delegate work that uses tools (Search grounding, code execution,
function calling), the number of API requests is **not** one-per-task. Get
this wrong and an "agentic" delegation burns through the 5-RPM ceiling in
seconds.

## Requests per turn, by pattern

| Pattern | Requests per turn | Notes |
|---|---|---|
| Plain text generation | 1 | Baseline |
| Built-in tools (Search, Map, Code Exec, URL Context) | **1** | Model iterates internally, returns final answer |
| Function calling (custom tools) | **2 per round** | Model proposes → execute → return → final response |
| Multi-turn function calling | **2 × N rounds** | 5-step workflow = 10 requests = burns 5 RPM in seconds |
| Search query inside grounded request | 1 (model side) + N billable searches | Search grounding has separate 1.5K-RPD bucket (free on 2.x only) |

**Implication:** multi-step agentic workflows on free tier are structurally
constrained. Either keep multi-step automation in your orchestrator, batch
tool calls aggressively, or use a paid key.

Single-shot built-in tools are way cheaper than they look.
`extract structured JSON from a search query with code-verified output` is
**one request** — the model iterates internally and returns the final answer.

## Tool combinability (Gemini 3.x)

Gemini 3.x supports combining ALL of these in **ONE** request:

- Structured Outputs (response schema)
- Google Search grounding
- URL Context
- Code Execution (Python sandbox)
- File Search
- Function Calling

This unlocks single-request workflows that previously needed 3–4 calls. Lean
on it for research + extraction + verification in one shot.

## Search grounding sub-quota

- **Gemini 2.x (free):** 1.5K RPD across all 2.x search-grounded calls.
- **Gemini 3.x (paid):** Search grounding is paid-only on 3.x — use 2.5 Flash
  if you need free search grounding (see [quotas.md](quotas.md)).

## Map grounding

Separate 500 RPD bucket on free tier. Use for location-aware tasks.
