# Free-tier quotas, paid-only models, and 429 diagnosis

> **Last verified:** 2026-05-20. If the date is older than ~4 weeks, run the
> package's `audit_keys` tool and check the AI Studio dashboard before
> trusting these numbers — Google rotates these.

Limits are **per Google Cloud project**, not per key. Each AI Studio account
allows up to **8 keys per project** (10 projects per account per docs, but
per-project key creation caps at 8). Pool throughput ceiling =
(number of projects) × (per-model RPM).

## Models you can route to safely (free tier)

| Model | RPM | TPM | RPD | Best for |
|---|---|---|---|---|
| `gemini-3.5-flash` | 5 | 250K | 20 | Default for writing, code-gen, anything needing thinking |
| `gemini-3.1-flash-lite` | 15 | 250K | **500** | The workhorse — 500 RPD is the best free quota |
| `gemini-3-flash` | 5 | 250K | 20 | Backup when 3.5 exhausted |
| `gemini-2.5-flash` | 5 | 250K | 20 | **Required for Search grounding** (paid on Gemini 3.x) |
| `gemini-2.5-flash-lite` | 10 | 250K | 20 | Cheapest non-Gemma free flash |
| `gemma-4-31b` | 15 | **Unlimited** | 1500 | **Batch + structured extraction** (unlimited TPM) |
| `gemini-embedding-2` | 100 | 30K | 1K | Embeddings |

## Paid-only — DO NOT route here without explicit user authorisation

These return `429 RESOURCE_EXHAUSTED` on every free-tier key:

- **Text:** `gemini-3.1-pro`, `gemini-3-pro`, `gemini-2.5-pro` (despite docs claiming free tier — dashboard reality is 0/0/0)
- **Image:** Nano Banana family (`gemini-2.5/3-flash-image`, `gemini-3-pro-image`), Imagen 4
- **Video:** Veo 2 / 3 / 3.1
- **Music:** Lyria 3
- **Agentic:** Computer Use Preview, Deep Research (3 variants)

## Diagnosing a 429

1. **Was the model paid-only?** Re-read the table above.
2. **Was it the model's RPM (5 or 15)?** Stagger dispatches with 12-second
   gaps if you're hammering one model from one project.
3. **Was it the model's RPD (20 or 500)?** Resets at midnight Pacific.
4. **Was it a tool sub-quota?** Search grounding has separate 1.5K-RPD on
   Gemini 2.x (**0 on 3.x — paid only**). Map grounding 500 RPD. Tools
   have their own buckets — see [cost-mechanics.md](cost-mechanics.md).
5. **Was it function-calling overhead?** Multi-turn workflows multiply
   requests — see [cost-mechanics.md](cost-mechanics.md).

## Key audit (June 19, 2026 deadline)

**Unrestricted keys stop working June 19, 2026.** Every key in `.env` must
be restricted to "Generative Language API" in AI Studio before then.

```bash
python3 -m gemini_key_pool.audit_keys
```

Run weekly. Writes a report to `logs/key-audit-YYYY-MM-DD.md` with
per-project status and a checklist for keys that need action.
