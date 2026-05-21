# Orchestration Patterns

Advanced multi-agent coordination patterns for complex workflows.

## Pattern Catalog

| Pattern | Use When | Agents | Coordination |
|---------|----------|--------|--------------|
| **Sequential Pipeline** | Clear stages, each depends on previous | 3-5 | Linear chain |
| **Parallel-Aggregate** | Multiple independent perspectives needed | 2-6 | Fork-join |
| **Hierarchical** | Complex planning + specialized execution | 1 manager + workers | Manager delegates |
| **Double-Diamond** | Creative exploration + critical analysis | 6-10 | Multi-phase |
| **Handoff Chain** | Iterative refinement, each adds value | 3-4 | Sequential handoff |

---

## Sequential Pipeline

Tasks execute in order where each stage depends on the previous stage's output.

```
Stage 1: Data Gathering → Stage 2: Analysis → Stage 3: Synthesis → Stage 4: Report
```

**When to Use:**
- Task has natural stages (research → analyze → report)
- Each stage requires different expertise or tools
- Stages cannot be parallelized

**Example: Content Research Pipeline**
```
Agent 1 (Data Gatherer): gemini-3-flash + google_search
  → Raw research data, URLs, key facts

Agent 2 (Analyst): gemini-3-pro + code_execution
  → Structured analysis with insights

Agent 3 (Writer): claude-sonnet
  → Polished article ready for publication
```

**Trade-offs:** Clear ownership, easy to debug | Cannot parallelize, bottlenecks cascade

---

## Parallel-Aggregate

Multiple agents work simultaneously on the same input, results aggregated by coordinator.

```
                ┌─ Agent A (Perspective 1) ─┐
Input ──────────┼─ Agent B (Perspective 2) ─┼──→ Aggregator → Final Output
                └─ Agent C (Perspective 3) ─┘
```

**When to Use:**
- Multiple valid perspectives exist (UX, Security, Performance)
- Want comprehensive coverage from different angles
- Time-sensitive (parallelization reduces total time)
- High throughput needed (4x with key rotation)

**Example: Comprehensive Code Review**
```
Parallel (gemini-3-flash each):
- Security Reviewer → vulnerabilities, injection, auth issues
- Performance Reviewer → bottlenecks, complexity, memory
- Code Quality Reviewer → style, maintainability, test coverage

Aggregator (claude-sonnet):
  → Unified review with prioritized action items
```

**Trade-offs:** Fastest pattern, comprehensive | Requires aggregation logic, more API calls

---

## Hierarchical Delegation

Manager agent coordinates workflow, delegating to specialized workers.

```
        Manager (Planner & Coordinator)
          ↓         ↓         ↓
       Worker1   Worker2   Worker3
          ↓         ↓         ↓
        Results validated by Manager
```

**When to Use:**
- Complex task requiring upfront planning
- Subtasks are heterogeneous
- Need quality validation and approval gates
- Manager needs to adjust plan based on results

**Example: Feature Implementation**
```
Manager (claude-sonnet): Analyze requirements, break down, assign, validate

Workers (gemini models):
- Database Specialist → schema design
- API Developer → REST endpoints
- UI Developer → React components
```

**Trade-offs:** Highest quality (validation) | Slowest pattern, coordination overhead

---

## Double-Diamond Ideation

Four-phase creative process: diverge → converge → diverge → converge.

```
DIAMOND 1: DISCOVER & DEFINE
Diverge (Generate 30+ ideas) → Converge (Select top 5-7)

DIAMOND 2: DEVELOP & DELIVER
Diverge (Analyze from 4+ lenses) → Converge (Final recommendation)
```

**When to Use:**
- Creative brainstorming with quality filter
- Strategic planning requiring diverse perspectives
- High-stakes decisions where thoroughness matters

**Phases:**
1. **Diverge**: 3 parallel ideators (creative, practical, user-centric) → 30+ ideas
2. **Converge**: Synthesizer (claude-sonnet) → top 5-7 ideas
3. **Diverge**: 4+ expert lenses analyze each idea
4. **Converge**: Decision maker (claude-opus) → final recommendation

**Trade-offs:** Most thorough | Most agent-intensive, longest execution

---

## Handoff Chain

Sequential refinement where each agent adds value building on previous work.

```
Draft → Enhance → Refine → Polish
```

**When to Use:**
- Task benefits from iterative refinement
- Each pass adds incremental value
- Quality improves with multiple passes

**Example: Content Creation**
```
Agent 1 (Drafter): gemini-3-flash → rough draft
Agent 2 (Structurer): gemini-3-flash → well-organized draft
Agent 3 (Polisher): claude-sonnet → publication-ready
```

**Trade-offs:** Incremental improvement | Sequential, risk of over-editing

---

## Structured Debate (Glass Box Asymmetric)

Two agents argue toward convergence under a Proposer / Critic protocol with
shared reasoning traces. An optional Judge calls convergence.

```
Round 1: Proposer (with CoT trace) ──► Critic ──► Critic critique (with CoT)
Round 2: Proposer responds / concedes ──► Critic ──► ...
... Judge declares convergence ─► Final answer
```

**When to use:**
- High-stakes decisions where a single agent's first answer is risky
- Topics where adversarial pressure improves output (correctness reviews, ambiguous specs)
- You want the reasoning trace alongside the conclusion (audit / explainability)

**Implementation sketch:**
1. Dispatch Proposer (`gemini-3-pro` or `gemini-3.5-flash`) with the task plus an instruction to emit `## Reasoning` alongside `## Answer`.
2. Dispatch Critic with the Proposer's full output and the prompt "find at least one substantive flaw with the reasoning, not just the conclusion."
3. Re-dispatch Proposer with the critique; it either defends with new reasoning or concedes.
4. Loop until a Judge agent (cheap model — `gemini-3.1-flash-lite`) declares convergence, OR a `--rounds` cap is hit.

Keep the Proposer/Critic on the same model to keep the comparison fair; the Judge can be cheaper.

**Trade-offs:** Highest reasoning rigor | 2–3× the requests of a single
delegation; usually pricier models for Proposer/Critic.

---

## Pattern Selection Guide

| Situation | Pattern |
|-----------|---------|
| Need speed + multiple perspectives | Parallel-Aggregate |
| Clear stages, dependencies | Sequential Pipeline |
| Complex planning + specialized work | Hierarchical |
| Creative brainstorming + evaluation | Double-Diamond |
| Iterative refinement | Handoff Chain |
| High-stakes decision needing adversarial pressure | Structured Debate |
| Quota-constrained | Sequential or Handoff |

---

## Best Practices

### Model Selection Per Pattern

- **Parallel-Aggregate**: Flash for parallel agents, Sonnet for aggregation
- **Sequential Pipeline**: Flash for early stages, Sonnet/Pro for final
- **Hierarchical**: Sonnet/Opus for manager, task-appropriate for workers
- **Double-Diamond**: Flash for diverge, Sonnet for converge, Opus for final

### Context Management

1. Pass rich context between agents (don't over-summarize)
2. Log intermediate outputs for debugging
3. Handle context limits by summarizing while preserving key details

### Error Handling

1. Graceful degradation if agent fails
2. Validation gates before next stage
3. Reasonable timeouts per agent
