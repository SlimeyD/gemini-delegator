# API Key Configuration

Setup guide for Gemini API keys. Required for using the orchestration system.

## Quick Setup

### 1. Get Gemini API Keys

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create API key(s) - recommend 4 keys for 4x throughput
3. Each key can be from a different Google Workspace account

### 2. Create Environment File

Create `.env` in the orchestration root:

```bash
# Gemini API Keys (4 keys for 4x throughput via rotation)
GEMINI_API_KEY_1=your_key_here
GEMINI_API_KEY_2=your_key_here
GEMINI_API_KEY_3=your_key_here
GEMINI_API_KEY_4=your_key_here

# Or use descriptive per-project names
PROJECT_A_GEMINI_API_KEY=your_key_here
PROJECT_B_GEMINI_API_KEY=your_key_here
PROJECT_C_GEMINI_API_KEY=your_key_here
PROJECT_D_GEMINI_API_KEY=your_key_here
```

### 3. Configure Key Pool

Create or update `orchestration/keys.json`:

```json
{
  "gemini_keys": [
    {"env_var": "GEMINI_API_KEY_1", "project": "project-1"},
    {"env_var": "GEMINI_API_KEY_2", "project": "project-2"},
    {"env_var": "GEMINI_API_KEY_3", "project": "project-3"},
    {"env_var": "GEMINI_API_KEY_4", "project": "project-4"}
  ],
  "rotation_strategy": "round_robin",
  "max_retries": 3,
  "retry_delay_ms": 1000
}
```

---

## Claude Desktop Configuration

If using in Claude Desktop/Cowork sessions:

### Domain Allowlist

Add `*.googleapis.com` to allowed domains:
1. Settings → Capabilities → Code execution and file creation
2. Allow network egress: ON
3. Additional allowed domains: `*.googleapis.com`

**Note:** Changes only apply to NEW Cowork sessions.

### Dependencies

Install in Cowork session:
```bash
pip install google-genai python-dotenv pyyaml httpx[socks] socksio
```

---

## Environment Variable for Exported Skill

When using the skill outside the original repo, set:

```bash
export MULTI_AGENT_ORCH_ROOT=/path/to/skill/folder
```

The scripts will:
1. Check `MULTI_AGENT_ORCH_ROOT` environment variable
2. Look for `SKILL.md` in parent directory (skill folder mode)
3. Fall back to repo-relative paths

---

## Key Rotation Benefits

With 4 keys:
- **4x RPM**: 60 requests/minute (vs 15 with single key)
- **Parallel execution**: Run 4 tasks simultaneously
- **Quota distribution**: Spread usage across accounts

---

## Troubleshooting

### API Key Not Working

1. Verify key is valid at [AI Studio](https://aistudio.google.com/)
2. Check `.env` file is in correct location
3. Ensure no trailing whitespace in key values

### Rate Limit Errors

1. Confirm all 4 keys are configured
2. Check `keys.json` rotation strategy
3. Add delay between requests if needed

### Network Errors in Cowork

1. Verify `*.googleapis.com` is in allowlist
2. Restart Claude Desktop (creates new session)
3. Check proxy settings if behind firewall

---

## Security Notes

- Never commit `.env` or `keys.json` with actual keys to git
- Add to `.gitignore`:
  ```
  .env
  orchestration/keys.json
  ```
- Use environment variables in production
- Rotate keys periodically
