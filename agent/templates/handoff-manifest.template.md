# Cross-Agent Handoff Manifest

> **From Executor**: {source_executor} ({source_platform})  
> **To Executor**: {target_executor} ({target_platform})  
> **Date**: {YYYY-MM-DD}  
> **Git Pin**: {git_sha} on branch `{branch}`  
> **Active Milestone**: {milestone_id}  
> **Handoff Mode**: executor  

---

## 1. Locked Decisions (DO NOT RE-OPEN)

The following Architectural Decision Records (ADRs) and design decisions are accepted and MUST NOT be relitigated:
- **ADR-01**: Persona D Native Execution (coordinator-delegate subagent architecture)
- {List additional relevant ADRs from agent/memory/decisions.md}

---

## 2. Completed Work (This Wave)

The following items were completed and committed:
- {Task-ID}: {Description} ([commit-hash])
- {Audit/Review}: {Report path or summary}

---

## 3. Pending Task Sequence (Immediate Priority)

The receiving agent MUST execute these tasks in the exact sequence specified:
1. **{task_id_1}**: {task_name} (est. tokens: {tokens_est}, complexity: {complexity})
2. **{task_id_2}**: {task_name} (est. tokens: {tokens_est}, complexity: {complexity})

---

## 4. Scope Guardrails (What NOT To Do)

To prevent regression and scope creep, the receiving agent MUST NOT:
- ❌ Re-open locked ADR decisions listed in Section 1
- ❌ Bypass the delegation threshold (> 50 line code changes must be delegated to isolated subagents)
- ❌ Skip the 4-stage quality gate (`/acp-review` → `/interrogate` → `/deslop` → `/acp-ci`)
- ❌ Commit directly to production branch (`mainline`)

---

## 5. Verification & Completion Criteria

Before declaring the handoff wave complete:
- [ ] All specified tasks marked completed in `agent/progress.yaml`
- [ ] Zero lint/type errors under `/acp-ci --static`
- [ ] Session summarized to `agent/memory/sessions.md` via `/acp-commit`
- [ ] Return handoff generated if passing back to coordinator: `/acp-handoff --mode executor --to {source_executor}`
