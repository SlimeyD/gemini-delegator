# gemini-delegator

**Gemini Delegator** is a high-throughput agent deployment skill for the Google Gemini API. It allows you to pool multiple API keys from different GCP projects to make the most of free-tier rate limits and provide a resilient, high-availability AI service.

---

## What It Does

Google's Gemini Free Tier is powerful but strictly limited (e.g., 500 requests per day for 3.1 Flash Lite). To scale beyond this, you need multiple projects and keys. **Gemini Key Pool** automates the orchestration of these keys by providing:

*   **Smart Key Rotation**: Uses Least-Recently-Used (LRU) selection to distribute load evenly across your pool.
*   **Fail-Safe Rate Limiting**: Automatically detects \`429 RESOURCE_EXHAUSTED\` errors and puts individual keys on tiered cooldowns (RPM, TPM, RPD).
*   **Model Fallback**: If your best model (e.g., Flash 3.5) is completely exhausted across all keys, the system automatically falls back to the next best model or a high quota alternative (e.g., Flash 3.0 or Flash 3.1 Lite).
*   **Concurrency Safety**: Built for parallel execution. Atomic reservations (\`reserve_key\`) prevent multiple agents from "thundering herd" on the same key.
*   **Persistent Usage Tracking**: Remembers rate-limit states across restarts using a file-locked JSON database.

---

## Setup Guide

### 1. Prerequisites
*   Python 3.10+
*   Multiple Gemini API keys (create them at [Google AI Studio](https://aistudio.google.com/app/apikey))
    *   Please note, limits apply per project - you can create up to 8 projects each with their own Gemini API key which can be given arbitrary names in your .env file.
    *   Please note: These will need to be mapped inside the keys.json file once set up to ensure the model_router.py is calling the right keys

### 2. Installation
\`\`\`bash
git clone https://github.com/SlimeyD/gemini-key-pool.git
cd gemini-key-pool
pip install -r requirements.txt
\`\`\`

### 3. Configuration

Setting up the pool requires two files in your project root: \`.env\` for the secrets and \`keys.json\` to define the pool structure.

#### Step 1: Create your \`.env\` file
Create a file named \`.env\` and add your API keys. Using descriptive names helps you track which key belongs to which project.

\`\`\`bash
# .env
GEMINI_KEY_PROJECT_1=AIzaSy...
GEMINI_KEY_PROJECT_2=AIzaSy...
GEMINI_KEY_PROJECT_3=AIzaSy...
\`\`\`

#### Step 2: Create your \`keys.json\` config
Create a file named \`keys.json\` to define how the pool should use those keys. The \`api_key\` field should use the \`env:\` prefix followed by the variable name from your \`.env\`.

\`\`\`json
{
  "providers": {
    "gemini": {
      "keys": [
        { "id": "primary-key", "api_key": "env:GEMINI_KEY_PROJECT_1" },
        { "id": "secondary-key", "api_key": "env:GEMINI_KEY_PROJECT_2" },
        { "id": "backup-key", "api_key": "env:GEMINI_KEY_PROJECT_3" }
      ]
    }
  }
}
\`\`\`

---

## Usage

### As a CLI Tool
The included \`gemini_agent.py\` is a powerful CLI for executing tasks:

\`\`\`bash
# Basic text generation
python3 -m gemini_key_pool.gemini_agent --task "Summarize this log" --output result.md

# Image generation (uses 2.5 Flash Image)
python3 -m gemini_key_pool.gemini_agent --task "A blueprint of a spaceship" --image-output ship.png

# High-quality research (uses Pro features via Flash if on free tier)
python3 -m gemini_key_pool.gemini_agent --task "Analyze market trends" --quality research --enable-tools
\`\`\`

### As a Python Library
Integrate the pool into your own applications:

\`\`\`python
from gemini_key_pool import KeyPoolManager, run_gemini_task

# 1. Direct key management
manager = KeyPoolManager()
key_id = manager.reserve_key("gemini") # Atomic reservation for thread-safety
try:
    api_key = manager.get_api_key(key_id)
    # ... your logic here ...
    manager.update_usage(key_id, {"requests": 1})
except Exception as e:
    # If it was a rate limit error, block the key
    manager.mark_key_rate_limited(key_id, error_message=str(e))
finally:
    manager.release_key(key_id)

# 2. High-level execution (handles rotation and retries automatically)
result = run_gemini_task(
    task="Write a blog post about AI safety",
    quality_level="production"
)
print(result["output"])
\`\`\`

---

## How It Works

### Tiered Cooldowns
The system parses Google's error messages to determine exactly how long to block a key:
*   **RPM (Per-Minute)**: 90 second cooldown.
*   **RPD (Per-Day)**: 1 hour cooldown (checked against Pacific Time resets).
*   **Quota (Billing)**: 2 hour cooldown.

### Model Fallback Chain
When a model is requested, the system attempts to fulfill it using the best available key. If the pool is empty for that model, it falls back:
\`Gemini 3.5 Flash\` → \`Gemini 3 Flash\` → \`Gemini 3.1 Flash Lite\` → \`Gemma 4 31B\` → \`Stop\`

Paid-only models (Pro variants, Nano Banana image models, Veo, Lyria, Computer Use, Deep Research) are gated behind a future \`--allow-paid\` flag and otherwise short-circuit to free equivalents.

---

## May 2026 Free Tier Reference (post Google I/O)
Verified empirically against live keys 2026-05-20. Limits are **per Google Cloud project** — multiple keys in one project share one bucket.

| Model | RPM | TPM | RPD | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Gemini 3.5 Flash** | 5 | 250K | 20 | New (I/O 2026), default choice |
| **Gemini 3 Flash** | 5 | 250K | 20 | Backup |
| **Gemini 3.1 Flash Lite** | 15 | 250K | 500 | Best free quota — the workhorse |
| **Gemini 2.5 Flash** | 5 | 250K | 20 | Required for Search grounding (paid on 3.x) |
| **Gemma 4 31B** | 15 | **Unlimited** | 1,500 | Batch + extraction (unlimited TPM!) |
| **Gemini 3.1 / 3 / 2.5 Pro** | 0 | 0 | 0 | Paid plan required |
| **Nano Banana, Veo, Lyria, Computer Use, Deep Research** | 0 | 0 | 0 | Paid plan required |

### Key restriction deadline — June 19, 2026
Google will block unrestricted API keys on **June 19, 2026** ([source](https://ai.google.dev/gemini-api/docs/api-key#secure-unrestricted-api-keys)). Every key must be restricted to "Generative Language API" via [AI Studio](https://aistudio.google.com/api-keys) before then. Use the included audit tool to track readiness:

\`\`\`bash
python3 -m gemini_key_pool.audit_keys
\`\`\`

This pings every \`*_GEMINI_API_KEY_*\` and \`GEMINI_API_KEY_*\` in your .env, classifies each as alive/blocked/expired/exhausted, and writes a per-project status report to \`logs/key-audit-YYYY-MM-DD.md\`.

---

## Testing
Run the suite of 42 tests to verify rotation, cooldowns, and locking logic:
\`\`\`bash
pytest tests/ -v
\`\`\`

## License
MIT
