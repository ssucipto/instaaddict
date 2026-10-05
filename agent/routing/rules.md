# Routing Rules — Human-readable complement to taxonomy.yml
# AI reads this when taxonomy.yml match is ambiguous

## Priority Order (when task spans multiple domains)
1. Task touches architecture or requires reasoning about the whole system → claude-sonnet
2. Task creates a NEW bash script from scratch (complex logic) → deepseek-v4-pro
3. Task creates a NEW command doc (complex directive writing) → deepseek-v4-pro
4. Task fixes or updates existing bash/command/TS → deepseek-v4-flash
5. Task only writes/updates tests → deepseek-v4-flash
6. Task runs tests locally → local-script
7. Default → deepseek-v4-pro

## Code Review Priority (v6.11.0, M55)
When routing a code review task:
1. Full-project review with all 54 rules + OWASP + MASVS → code-review-full (copilot)
2. Security-only review (--rules security) → code-review-security (copilot)
3. Targeted review with --rules flag (1-2 categories) → code-review-targeted (deepseek-v4-pro)
4. CI pipeline review with --ci flag → code-review-ci (qwen3-235b)
5. Flash/Flash-Max are DISQUALIFIED for all review tasks — cannot sustain cross-file reasoning

## Override Triggers
- Developer adds `override_executor: [model]` to task frontmatter → use that model
- Task has `risk: critical` → escalate to claude-sonnet regardless of other rules
- Task is in lessons.md with a routing correction → follow lessons.md

## Ambiguity Resolution
When a task could be either command-doc-write or bash-script-create:
  - If the primary output is a .md file → command-doc-write
  - If the primary output is a .sh file → bash-script-create
  - If both → bash-script-create (higher complexity, drives the command doc)

When uncertain between deepseek-v4-flash and deepseek-v4-pro:
  - Prefer flash for tasks ≤ 3 files and no cross-component reasoning
  - Prefer pro for tasks touching acp.common.sh or the YAML parser

When uncertain between command-doc-write and command-doc-update:
  - Adding a new protocol section with > 20 lines of new directive text → command-doc-write
  - Updating/correcting existing content (< 20 net new lines) → command-doc-update
  - Rewriting > 50% of an existing command doc → command-doc-write
  - New route with no existing command doc at all → command-doc-write

## Persona D: Antigravity + Agystack Execution Rules (v6.41.0)
When operating inside Google Antigravity with the Agystack plugin active:
1. **Coordinator Role**: The parent chat session serves as coordinator (planning, review, verification, and memory maintenance).
2. **Subagent Delegation Invariant**: All non-trivial code modifications (> 50 lines on a single file, or multi-file code changes) MUST be delegated to `poteto-agent` via `invoke_subagent`. Small configuration edits, markdown documentation, `.gitignore`, and scratch scripts are permitted directly by the coordinator. When operating in an environment where subagent spawning is disallowed or subagent tools are unavailable, the coordinator satisfies this invariant by executing and owning the diff directly with heightened verification.
3. **Model Tier Mapping**:
   - `pro`: High-reasoning tasks (`architecture-plan`, `design-document`, `bash-script-create`, `bash-script-refactor`, `bug-fix-complex`, `code-review-full`, `code-review-security`, `code-integrity-scan`, `parallel orchestrator`).
   - `flash`: Fast mechanical tasks (`command-doc-update`, `bash-script-fix`, `yaml-schema`, `e2e-test-write`, `typescript-feature`, `documentation-sync`, `wiki-update`, `memory-write`, `changelog-update`, `progress-update`).
   - `inherit`: Interactive parent chat coordination, milestone tracking, and task routing.
4. **Execution Protocol**:
   - Coordinator authors `implementation_plan.md` in `<appDataDir>/brain/<conversation-id>/`.
   - Code delegate writes implementation in isolated subagent context.
   - Coordinator reviews diff, runs tests, executes `/deslop`, and verifies compliance with `/acp-ci`.
   - Results stamped to `agent/memory/sessions.md` via `/acp-commit`.

