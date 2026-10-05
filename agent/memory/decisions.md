# Architecture Decision Records (ADR Log)
# Loaded by section (ADR ID) only — never fully loaded
# Add entries via /acp-decide command

## ADR-01 | 2026-10-05 | Establish Persona D for Antigravity + Agystack Native Execution
**Status:** Accepted
**Context:** ACP Enhanced supported three execution personas: A (GitHub Copilot inline), B (external LLM dispatch via OpenRouter/DeepSeek), and C (mixed). When operating inside Google Antigravity with the Agystack plugin, none of these personas mapped correctly. Antigravity provides native subagent delegation (`invoke_subagent`), tiered model selection (`pro`, `flash`, `inherit`), and the `poteto-agent` code delegate. These capabilities are strictly more powerful than external dispatch but require different orchestration rules.
**Options considered:**
1. Reuse Persona A with manual model overrides — rejected because Copilot inline mode has no subagent delegation
2. Reuse Persona B with Antigravity as an external executor — rejected because it adds unnecessary network hops and loses native scheduling
3. Create a thin adapter mapping Antigravity tools to Persona C — rejected because C's hybrid mode introduces ambiguity about which executor owns each step
4. Establish Persona D as a first-class native mode — accepted
**Decision:** Create Persona D ("Antigravity + Agystack Native") with its own executor (`antigravity-agystack`), model tier mappings (`pro`, `flash`, `inherit`), and delegation rules (>50 line edits delegate to `poteto-agent`). Task types in `taxonomy.yml` carry an `antigravity_tier` field. The coordinator-delegate separation mirrors Agystack's AGENTS.md rules while preserving ACP's persistent memory layers.
**Consequences:** Persona D sessions bypass external dispatch entirely. The routing taxonomy must carry dual executor fields (one for B/C personas, one for D). Cross-platform portability requires a platform adapter layer mapping subagent primitives to each target's native tools.
**DO NOT re-open** unless Antigravity deprecates `invoke_subagent` or Agystack fundamentally changes its delegation model.

