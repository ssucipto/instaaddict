# Upstream Architecture Proposal: Persona D ("Antigravity + Agystack Native") & Subagent Delegation Layer for ACP Enhanced

**Document**: RFC-2026-001  
**Author**: ACP & Agystack Integration Engineering  
**Date**: 2026-10-05  
**Target Release**: ACP Enhanced v6.42.0+  
**Status**: Proposed / Shipped in Dogfood Reference Implementation  

---

## 1. Motivation & Background

ACP Enhanced has historically supported three execution personas:
- **Persona A**: Single-model inline chat (GitHub Copilot).
- **Persona B**: External API dispatch to specialized models via OpenRouter or DeepSeek scripts.
- **Persona C**: Hybrid inline and external dispatch.

While these personas served early chat-centric workflows well, modern agentic environments like **Google Antigravity**, **Claude Code**, and **Cursor** introduce powerful first-class capabilities:
- Native background subagents (`invoke_subagent`, `Task`).
- Reactive asynchronous scheduling (`schedule` watchdog timers).
- Distinct model tiering (`pro`, `flash`, `inherit`).
- Playbook-driven engineering with anti-slop cleaning and adversarial reviews.

Operating inside modern IDEs using legacy personas creates friction:
1. **Context Window Starvation**: Large code edits directly in the main conversation exhaust context limits and lead to forgotten instructions.
2. **Economic Inefficiency**: Simple tasks (YAML updates, documentation, tests) consume expensive frontier reasoning tokens because no tiering mechanism exists.
3. **No Subagent Boundary**: The lack of a formal threshold for when to delegate code modifications vs keep them in the coordinator.

To bridge this gap, this proposal establishes **Persona D** as an official, first-class native execution mode in ACP Enhanced.

---

## 2. Core Architectural Pillars of Persona D

### Pillar 1: Coordinator-Delegate Separation
- **Coordinator (Parent Chat)**: Dedicated strictly to session planning, reading context, reviewing diffs, running verification gates, and maintaining persistent memory (`sessions.md`, `patterns.md`, `decisions.md`).
- **Delegate (`poteto-agent`)**: Invoked in an isolated subagent context to execute non-trivial code modifications (>50 lines on a single file, or multi-file edits). When work finishes, it reports back with pure technical summaries, leaving the coordinator context pristine.

```
┌────────────────────────────────────────────────────────┐
│             Coordinator (Parent Chat Session)          │
│  - Loads ACP Context (Core → Taxonomy → Skill → Memory)│
│  - Authors implementation_plan.md                      │
│  - Reviews Diffs, Runs /acp-ci, Updates sessions.md    │
└───────────────────────────┬────────────────────────────┘
                            │ invoke_subagent (>50 lines)
                            ▼
┌────────────────────────────────────────────────────────┐
│          Delegate (Isolated poteto-agent Subagent)     │
│  - Executes code modifications in clean context        │
│  - Zero conversation bloat or prose overhead           │
│  - Returns diff & receipts to coordinator              │
└────────────────────────────────────────────────────────┘
```

### Pillar 2: Single-Pass Model Tiering in Taxonomy
Instead of disconnected external lookup tables, each task type in `agent/routing/taxonomy.yml` carries inline metadata:
```yaml
bug-fix-complex:
  executor: deepseek-v4-pro        # Persona B/C
  antigravity_tier: pro            # Persona D tier (pro, flash, inherit)
  delegation_required: true        # Persona D subagent threshold
  complexity: medium
  context_required: [wiki/architecture.md, memory/sessions.md, memory/decisions.md]
  tokens_est: 12000
```
This enables single-pass resolution with zero runtime branching complexity.

### Pillar 3: 4-Stage Dual Quality Gate
Enhances ACP's deterministic `/acp-review` command with Agystack's adversarial multi-model reviews and slop purging:
1. **Stage 1 (Standards)**: `/acp-review` (64 rules).
2. **Stage 2 (Adversarial)**: `/interrogate` (independent multi-model challenge).
3. **Stage 3 (Cleanliness)**: `/deslop` (strips comment narration, speculative error handling, and artificial padding).
4. **Stage 4 (Pre-Push CI)**: `/acp-ci` (local deterministic test execution).

---

## 3. Specification of Changes

### 3.1. `agent/core/routing.yml`
Add Persona D definition:
```yaml
session:
  executor: antigravity-agystack  # Antigravity native coordinator with poteto-agent delegation
  model: gemini-3.8-flash        # Active session model tier or inherit
  persona: D                     # A (copilot-only), B (deepseek-only), C (mixed), D (antigravity-agystack)
```

### 3.2. `agent/routing/rules.md`
Add section documenting Persona D execution rules:
```markdown
## Persona D: Antigravity + Agystack Execution Rules
1. **Coordinator Role**: Parent chat session manages planning, review, memory, and verification.
2. **Subagent Delegation Invariant**: Non-trivial code edits (>50 lines or multi-file) delegate to `poteto-agent` via `invoke_subagent`. Trivial edits (<=50 lines, configs, docs) execute in coordinator. In environments without subagent tools, coordinator executes directly with heightened verification.
3. **Model Tier Mapping**:
   - `pro`: High-reasoning tasks (architecture, security, complex refactors).
   - `flash`: Fast mechanical tasks (tests, schemas, docs, quick fixes).
   - `inherit`: Interactive parent chat coordination, milestone tracking, audits.
```

### 3.3. `agent/commands/acp.proceed.md`
Add conditional delegation hook in Step 2:
```markdown
> **Persona D Branch (Antigravity + Agystack Native)**:
> If operating under Persona D (`antigravity-agystack`), evaluate the delegation threshold:
> - **Non-trivial code modification** (> 50 lines on a single file, multi-file code changes, core business logic):
>   1. Author `implementation_plan.md` in `<appDataDir>/brain/<conversation-id>/`
>   2. Delegate implementation to `poteto-agent` via `invoke_subagent`
>   3. Coordinator inspects delegate diff, runs `/deslop`, and verifies via `/acp-ci`
> - **Trivial edits** (<= 50 lines, markdown documentation, `.gitignore`, single flag changes, scratch scripts):
>   Implement directly in coordinator context without spawning a subagent.
```

### 3.4. Bridge Script (`scripts/acp_agystack_bridge.py`)
Provides runtime preflight checks (`--doctor`), taxonomy tier alignment diagnostics (`--status`), and configuration synchronization (`--sync`).

---

## 4. Cross-Platform Generalization

This integration also establishes universal portability:
- **Rule file mapping**: `AGENTS.md` (Antigravity) ↔ `CLAUDE.md` (Claude Code) ↔ `.cursorrules` (Cursor).
- **Subagent primitives**: `invoke_subagent` (Antigravity) ↔ `Task` (Claude Code) ↔ Composer sub-workers (Cursor).
- **State handoff**: Standardized `handoff-manifest.template.md` allows seamless transfer between agents without context loss.

---

## 5. Implementation & Rollout Plan

1. **Phase 1 (Merged in reference)**: Persona D definition, taxonomy inlining, `acp.agystack.md`, and bridge script.
2. **Phase 2 (Release Candidates)**: Add unit tests in upstream ACP test suite for `acp_agystack_bridge.py` and taxonomy parsing.
3. **Phase 3 (Documentation & Release)**: Update ACP README, architectural wiki, and publish in the next minor version bump (v6.42.0).
