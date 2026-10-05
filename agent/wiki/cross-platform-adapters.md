# Cross-Platform Adapters: Agystack + ACP Enhanced

> **Status:** Active — Shipped in v6.41.0 (Audit-145)  
> **Purpose:** Standardize the execution, subagent delegation, quality gates, and handoff protocols across Google Antigravity, Claude Code, Cursor, and GitHub Copilot.

---

## 1. Architectural Philosophy

ACP Enhanced provides **structured persistent memory and task routing** (sessions, lessons, patterns, decisions, carryovers, routing taxonomy).  
Agystack provides **rigorous agentic execution playbooks and subagent isolation** (coordinator-delegate separation, 23 playbooks, 21 principles, multi-model review, deslop).

The unified stack separates concerns:
- **Project State & Memory**: Platform-independent files stored under `agent/` in the repository filesystem.
- **Orchestration & Coordination**: Parent agent sessions handle context loading, planning, review, and verification.
- **Execution & Code Modification**: Isolated subagents handle non-trivial code modifications (> 50 lines).

---

## 2. Platform Primitive Mappings

| Feature / Primitive | Google Antigravity | Claude Code | Cursor (Composer/pstack) |
|---|---|---|---|
| **Rule Entrypoint** | `AGENTS.md` / plugin rules | `CLAUDE.md` / `.claude/` | `.cursorrules` / `.cursor/rules/` |
| **Active Persona** | Persona D (`antigravity-agystack`) | Persona B/D adapter | Persona A/D adapter |
| **Subagent Delegation** | `invoke_subagent` (`poteto-agent`) | `Task` tool with isolated context | Composer sub-worker / pstack delegate |
| **Watchdog Timer** | `schedule(TimerCondition: "never")` | Background bash sleep loop | Task timeout / manual check |
| **Reactive Wakeup** | Automatic on subagent message | Subprocess return code | Composer thread update |
| **Scratch / Brain Artifacts** | `<appDataDir>/brain/<id>/` | `.claude/scratch/` or `/tmp/` | `.cursor/artifacts/` or project temp |
| **Model Tiers** | `pro`, `flash`, `inherit` | Model selector (Sonnet 3.7, Haiku) | Cursor model picker (Claude, GPT-4o) |
| **Adversarial Review** | `/interrogate` (multi-tier subagents) | Multi-turn prompt or dual-agent loop | Parallel composer / chat tabs |
| **Slop Cleanup** | `/deslop` (skill) | `/deslop` prompt or script | Manual / prompt pass |
| **Verification Gate** | `/acp-ci` + `/acp-review` | Local bash CI runner | Built-in terminal tests |

---

## 3. The 4-Stage Dual Quality Gate

Regardless of platform, code must pass all four gates prior to staging and PR creation:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ 1. Standards    │ ──> │ 2. Adversarial  │ ──> │ 3. Cleanliness  │ ──> │ 4. Pre-Push CI  │
│ /acp-review     │     │ /interrogate    │     │ /deslop         │     │ /acp-ci         │
│ (64 rules)      │     │ (multi-model)   │     │ (anti-slop)     │     │ (test suite)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
```

1. **Standards Gate (`/acp-review`)**: 64-rule scan (OWASP Top 10, MASVS, TypeScript strict, bash safety, ACP conventions).
2. **Adversarial Gate (`/interrogate`)**: Multi-model independent audit challenging race conditions, edge cases, and failure modes.
3. **Cleanliness Gate (`/deslop`)**: Strips comment narration, speculative guards, redundant error handling, and artificial padding.
4. **Pre-Push CI Gate (`/acp-ci`)**: Local deterministic static and matrix test suites verifying zero regression.

---

## 4. Cross-Platform Handoff Protocol

When transferring work between different agents or platforms (e.g. Antigravity → Claude Code, or Claude Code → Cursor):

1. **Commit Current Session**: Execute `/acp-commit` to record completed tasks, deferred items, and key facts to `agent/memory/sessions.md`.
2. **Pin State**: Record the exact `git rev-parse HEAD` and current branch.
3. **Generate Handoff Manifest**: Create `agent/reports/handoff-{target}-{date}.md` using the standard handoff manifest template.
4. **Update Pointer**: Overwrite `agent/reports/HANDOFF-LATEST.md` with the new handoff content.
5. **Receiving Session Boot**: On the incoming agent:
   - Run `/acp-init` to load project context.
   - Run `/acp-receive agent/reports/HANDOFF-LATEST.md` to verify git pin, lock ADRs, and load current task sequence.
