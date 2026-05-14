# Model Capabilities

Quick reference for model selection in orchestration workflows.

## Gemini 3 Family (Primary - January 2026)

### gemini-3-flash
- **API Name**: `gemini-3-flash-preview`
- **Context**: 1M tokens | **Output**: 65K tokens
- **Speed**: Very fast (~200ms latency)
- **Cost**: Free tier

**Best For:**
- Format, list, summarize, translate, convert (simple tasks)
- Draft, brainstorm, iterate, prototype (rapid iteration)
- Batch, bulk, volume processing (high throughput)

**Avoid For:**
- Strategic, novel, creative, complex synthesis (use Pro or Claude)

**Thinking**: Supports levels [minimal, low, medium, high]

### gemini-3-pro
- **API Name**: `gemini-3-pro-preview`
- **Context**: 1M tokens | **Output**: 65K tokens
- **Speed**: Medium (~1000ms latency)
- **Cost**: Free tier

**Best For:**
- Analyze, architect, design, complex, review (deep reasoning)
- Code, debug, refactor, security (technical reasoning)
- Plan, strategy, evaluate, compare (multi-step analysis)

**Avoid For:**
- Simple, quick, format, list (use Flash)

**Thinking**: Supports levels [low, high]

### gemini-3-pro-image-preview
- **API Name**: `gemini-3-pro-image-preview`
- **Context**: 65K tokens | **Output**: 32K tokens
- **Speed**: Medium (~2000ms latency)

**Best For:**
- Professional, brand, marketing, production images
- Asset, mockup, design, visual content
- High-fidelity text rendering in images

---

## Gemini 2.5 Family (Stable Fallback)

### gemini-2.5-flash
- **API Name**: `gemini-2.5-flash`
- **Fallback for**: gemini-3-flash
- **Thinking**: Budget-based [0-24576 tokens]

### gemini-2.5-pro
- **API Name**: `gemini-2.5-pro`
- **Fallback for**: gemini-3-pro
- **Thinking**: Budget-based [128-32768 tokens]

### gemini-2.5-flash-image
- **API Name**: `gemini-2.5-flash-image`
- Fast image generation for high-volume/draft tasks

---

## Claude Models

### claude-sonnet-4.5
- **Context**: 200K tokens | **Output**: 16K tokens
- **Cost**: $0.003/1K input, $0.015/1K output
- **Speed**: Fast (~1000ms)

**Best For:**
- Synthesize, combine, judgment, nuanced (synthesis tasks)
- MCP tools (Linear, GitHub, Supabase) - **Required**
- Code review, refactor, debug, implement
- Production, final, customer-facing outputs

**Avoid For:**
- Simple, bulk, batch, high-volume (use Gemini)

### claude-opus-4.5
- **Context**: 200K tokens | **Output**: 32K tokens
- **Cost**: $0.015/1K input, $0.075/1K output
- **Speed**: Slow (~3000ms)

**Best For:**
- Strategic, novel, creative, groundbreaking
- Complex synthesis, multi-document, deep analysis, research
- Critical, important, high-stakes, production

**Avoid For:**
- Simple, quick, draft, routine, batch (too expensive)

---

## Quality Tier Routing

| Quality | Primary Model | Use Case |
|---------|--------------|----------|
| **Draft** | gemini-3-flash | Quick iterations, brainstorming |
| **Standard** | gemini-3-flash (medium thinking) | Everyday tasks, internal use |
| **Production** | gemini-3-pro or claude-sonnet | Final outputs, customer-facing |
| **Research** | claude-opus | Strategic decisions, deep analysis |

---

## Key Rotation (4x Throughput)

4 Gemini API keys rotate automatically:
- Effective RPM: 60 (Flash), 40 (Pro)
- Configuration: `orchestration/keys.json`

---

## Fallback Chain

```
gemini-3-flash → gemini-2.5-flash
gemini-3-pro → gemini-2.5-pro
claude-sonnet → claude-opus
claude-opus → gemini-3-pro (emergency)
```

---

## Capabilities Matrix

| Model | Multimodal | Code Exec | Search | MCP Tools |
|-------|------------|-----------|--------|-----------|
| gemini-3-flash | Yes | Yes | Yes | No |
| gemini-3-pro | Yes | Yes | Yes | No |
| claude-sonnet | Vision only | No | No | Yes |
| claude-opus | Vision only | No | No | Yes |
