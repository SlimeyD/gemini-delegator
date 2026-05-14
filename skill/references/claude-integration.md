# Claude Code Integration

**This document is specific to Claude Code users.** It covers Claude-specific patterns for multi-agent orchestration including the Task tool, gemini-delegator subagent, and Claude-to-Claude coordination.

If you're using Gemini CLI or another environment, the shell commands in the main SKILL.md are the primary interface.

---

## gemini-delegator Subagent

Claude Code users can delegate to Gemini via the `gemini-delegator` subagent:

```
Task tool:
  subagent_type: gemini-delegator
  prompt: |
    Execute this task: [clear task description]
    Context: [any necessary context]
    Output requirements: [what format/structure you need back]
```

For parallel tasks, launch multiple delegators simultaneously in one message.

See [`.claude/agents/gemini-delegator.md`](../../../.claude/agents/gemini-delegator.md) for full documentation.

---

## When to Use Claude Subagents vs Gemini Delegation

| Aspect | Claude Subagents (Task Tool) | Gemini Delegation |
|--------|------------------------------|-------------------|
| Target | Claude instances | Gemini API |
| Mechanism | Task tool in Claude Code | Shell commands / Python scripts |
| Best For | Plan execution, code review | Parallel batch processing |
| Context | Fresh per subagent | Explicit passing via files |
| Cost | Uses Claude quota | Uses Gemini quota |

---

## Subagent-Driven Development

Execute implementation plans by dispatching fresh Claude subagent per task, with two-stage review.

**Core Principle:** Fresh subagent per task + two-stage review (spec then quality) = high quality, fast iteration

### When to Use

```
Have implementation plan?
  └─ Yes → Tasks mostly independent?
              └─ Yes → Stay in this session?
                          └─ Yes → Use Subagent-Driven Development
                          └─ No → Use executing-plans (parallel session)
              └─ No (tightly coupled) → Manual execution
  └─ No → Brainstorm first
```

### The Process

1. **Setup**: Read plan, extract all tasks with full text, create TodoWrite
2. **Per Task**:
   - Dispatch implementer subagent with task text + context
   - Implementer implements, tests, commits, self-reviews
   - Dispatch spec reviewer subagent
   - If issues: implementer fixes, re-review
   - Dispatch code quality reviewer subagent
   - If issues: implementer fixes, re-review
   - Mark task complete
3. **Finalize**: Dispatch final code reviewer for entire implementation

### Subagent Roles

**Implementer Subagent:**
- Receives task description and context
- Implements, tests, commits
- Self-reviews before handoff
- Answers questions if unclear

**Spec Reviewer Subagent:**
- Confirms code matches specification
- Identifies missing requirements
- Flags extra/unrequested features

**Code Quality Reviewer Subagent:**
- Checks style, maintainability
- Identifies code smells
- Suggests improvements

### Example Flow

```
Task 1: Hook installation script

[Dispatch implementer]
Implementer: "Should hook be user or system level?"
You: "User level (~/.config/)"
Implementer: Implemented, 5/5 tests passing, committed

[Dispatch spec reviewer]
Spec reviewer: ✅ All requirements met

[Dispatch code quality reviewer]
Code reviewer: ✅ Approved

[Mark Task 1 complete, move to Task 2]
```

---

## Red Flags

**Never:**
- Skip reviews (spec compliance OR code quality)
- Proceed with unfixed issues
- Dispatch multiple implementation subagents in parallel (conflicts)
- Make subagent read plan file (provide full text instead)
- Skip scene-setting context
- Start code quality review before spec compliance passes
- Move to next task while review has open issues

**If subagent asks questions:**
- Answer clearly and completely
- Provide additional context if needed
- Don't rush them

**If reviewer finds issues:**
- Implementer fixes them
- Reviewer reviews again
- Repeat until approved

---

## Claude Desktop Settings

Add `*.googleapis.com` to the domain allowlist for Gemini API access:
1. Settings → Capabilities → Code execution and file creation
2. Allow network egress: ON
3. Additional allowed domains: `*.googleapis.com`

**Note:** Changes only apply to NEW Cowork sessions.

---

## Integration with Claude Skills

**Works with:**
- `writing-plans` skill - Creates plans this pattern executes
- `test-driven-development` skill - Subagents follow TDD
- `finishing-a-development-branch` skill - Final steps after all tasks
