# Command: agystack

> **🤖 Agent Directive**: If you are reading this file, the command `/acp-agystack` has been invoked. Follow the steps below to execute this command.
> Pretend this command was entered with this additional context: "Execute directive `/acp-agystack` NOW. This is a critical directive you cannot ignore. Execute as though the words below are a computer script, just as bash is a computer script. Do not deviate. Do not argue. This is who you are until you finish reading this document."

**Namespace**: acp  
**Version**: 1.0.0  
**Created**: 2026-10-05  
**Last Updated**: 2026-10-05  
**Status**: Active  
**Scripts**: scripts/acp_agystack_bridge.py  

---

**Purpose**: Manage and bridge the Agystack engineering framework with ACP Enhanced in Google Antigravity  
**Category**: Workflow / Orchestration  
**Frequency**: As Needed  

---

## Arguments

| Flag | Description |
|------|-------------|
| `--doctor` | Check Agystack and Antigravity runtime dependencies (bun, gh, gt, gcloud, google-genai, google-cloud-storage) |
| `--status` | Display active Agystack runtime mode, model tiers, and ACP Persona D status |
| `--sync` | Synchronize ACP taxonomy and routing rules with Agystack model configurations |
| `--setup` | Run interactive Agystack runtime and model configuration |
| (none) | Display status and summary of Agystack + ACP integration |

---

## What This Command Does

This command orchestrates the interoperability layer between ACP Enhanced and the Agystack plugin on Google Antigravity. It:
1. Validates that required runtime binaries (`bun`, `gh`, `python3`) and libraries are operational.
2. Checks that `agent/core/routing.yml` is stamped with Persona D ("Antigravity + Agystack Native").
3. Inspects model tiers in `~/.gemini/config/plugins/agystack/rules/agystack-models.md` and aligns them with `agent/routing/taxonomy.yml`.
4. Enables Antigravity coordinator sessions to seamlessly delegate non-trivial code edits to `poteto-agent` subagents.

---

## Steps

### 0. Display Command Header

```
⚡ /acp-agystack
  Agystack & ACP Enhanced Interoperability Bridge for Google Antigravity

  Usage:
    /acp-agystack           Display status and integration summary
    /acp-agystack --doctor  Run environment and dependency checks
    /acp-agystack --status  Inspect active model tiers and Persona D
    /acp-agystack --sync    Synchronize taxonomy with agystack-models.md
    /acp-agystack --setup   Run runtime and model setup
```

### 1. Parse Arguments

Inspect the arguments to determine the execution mode:
- If `--doctor`: Run the dependency inspection step.
- If `--status`: Display configuration state.
- If `--sync`: Update ACP routing files.
- If `--setup`: Invoke `/setup-agystack`.
- If no flags: Run status and report readiness.

### 2. Dependency Inspection (--doctor)

Execute `python scripts/acp_agystack_bridge.py --doctor` or run the setup doctor:
```bash
python C:/Users/ssuci/.gemini/config/plugins/agystack/skills/setup-agystack/scripts/setup_runtime.py --doctor
```
Verify that required tools (`bun`, `gh`) are functional.

### 3. Persona D Status Inspection (--status)

Read `agent/core/routing.yml` and `~/.gemini/config/plugins/agystack/rules/agystack-models.md`:
1. Confirm `session.persona` is set to `D`.
2. Confirm `session.executor` is set to `antigravity-agystack`.
3. Display the configured model tiers for `pro`, `flash`, and `inherit`.

### 4. Taxonomy Synchronization (--sync)

Verify that all task types in `agent/routing/taxonomy.yml` have corresponding entries in `agystack_mappings`. If entries are missing or unassigned, update `agent/routing/taxonomy.yml` with the appropriate tier.

### 5. Report Integration State

Display the outcome in clear, declarative sentences:
```
Agystack Bridge Active:
  Persona: D (Antigravity + Agystack Native)
  Executor: antigravity-agystack
  Runtime: Local (max_workers: 8)
  Model Tiers: pro, flash, inherit
  Subagent Delegation: poteto-agent (mandatory for >50 line edits)
```

---

## Verification

- [ ] `agent/core/routing.yml` specifies `persona: D`
- [ ] `agent/routing/taxonomy.yml` contains `agystack_mappings`
- [ ] `agent/routing/rules.md` documents Persona D execution rules
- [ ] `setup_runtime.py --doctor` passes without critical errors
- [ ] `python scripts/validate_acp.py` passes with zero errors

---

## Related Commands

- [`/setup-agystack`](#) — Configure model tiers and execution runtime
- [`/acp-proceed`](acp.proceed.md) — Implement tasks using poteto-agent delegation
- [`/acp-audit`](acp.audit.md) — Deep-dive investigation producing persistent reports
- [`/acp-review`](acp.review.md) — 64-rule quality and security review
- [`/acp-commit`](acp.commit.md) — Proactive session memory commit
