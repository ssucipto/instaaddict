#!/bin/bash
# Generate Zed slash commands (.agents/skills/ and .zed/) from ACP command sources.
# Maps agent/commands/acp.init.md -> .agents/skills/acp-init/SKILL.md and .zed/settings.json

set -euo pipefail
trap 'echo "Error: acp.zed-commands-sync.sh failed at line $LINENO" >&2; exit 3' ERR

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

if command -v python >/dev/null 2>&1; then
  python "$ROOT/scripts/sync_zed_commands.py"
elif command -v python3 >/dev/null 2>&1; then
  python3 "$ROOT/scripts/sync_zed_commands.py"
else
  echo "Python not found, skipping Zed slash commands generation."
fi
