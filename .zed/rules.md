# ACP Enhanced Instructions for Zed

This repository operates under the **Agent Context Protocol (ACP) Enhanced** framework.

## Context Loading Protocol
Before executing tasks or slash commands:
1. Always load and respect `AGENTS.md` (and `agent/core/identity.yml`, `agent/core/constraints.yml`).
2. When a slash command like `/acp-init`, `/acp-route`, `/acp-status`, or `/acp-commit` is used, execute the workflow specified in the corresponding `agent/commands/acp.*.md` document.
3. Follow the context budget and session memory commit protocol (`/acp-commit`).
