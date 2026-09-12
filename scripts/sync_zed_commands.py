import os
import glob
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CMD_DIR = os.path.join(ROOT, "agent", "commands")
SKILLS_DIR = os.path.join(ROOT, ".agents", "skills")
ZED_DIR = os.path.join(ROOT, ".zed")

os.makedirs(SKILLS_DIR, exist_ok=True)
os.makedirs(ZED_DIR, exist_ok=True)

def extract_purpose(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("**Purpose**:"):
                return line.replace("**Purpose**:", "").strip()
    return "ACP Enhanced command"

cmd_files = sorted(
    glob.glob(os.path.join(CMD_DIR, "acp.*.md"))
    + glob.glob(os.path.join(CMD_DIR, "git.*.md"))
    + glob.glob(os.path.join(CMD_DIR, "local.*.md"))
)

slash_commands_settings = {}
count = 0

for file_path in cmd_files:
    base = os.path.basename(file_path)
    name = os.path.splitext(base)[0]
    slash_name = name.replace(".", "-")
    purpose = extract_purpose(file_path).replace('"', '\\"')

    # 1. Create .agents/skills/<slash_name>/SKILL.md
    skill_folder = os.path.join(SKILLS_DIR, slash_name)
    os.makedirs(skill_folder, exist_ok=True)
    skill_file = os.path.join(skill_folder, "SKILL.md")

    skill_content = f"""---
name: {slash_name}
description: "{purpose}"
---

# ACP Command: /{slash_name}

Execute ACP Enhanced command `/{slash_name}`.

1. Read and follow **every step** in `agent/commands/{base}`.
2. Treat text after the command in the user's message as command arguments.
3. Run the command header from the source file, then continue unless the source explicitly waits for input.

**Canonical source**: `agent/commands/{base}`
**Equivalent invocations**: `/{slash_name}`, `@{slash_name}`, `@agent/commands/{base}`
"""
    with open(skill_file, "w", encoding="utf-8", newline="\n") as f:
        f.write(skill_content)
    count += 1

    # 2. Add to slash_commands for .zed/settings.json
    slash_commands_settings[slash_name] = {
        "description": purpose,
        "text": f"Execute ACP Enhanced command `/{slash_name}`.\n\n1. Read and follow **every step** in `agent/commands/{base}`.\n2. Treat text after the command in the user's message as command arguments.\n3. Run the command header from the source file, then continue unless the source explicitly waits for input.\n\n**Canonical source**: `agent/commands/{base}`"
    }

# 3. Create .zed/settings.json
zed_settings_file = os.path.join(ZED_DIR, "settings.json")
existing_settings = {}
if os.path.exists(zed_settings_file):
    try:
        with open(zed_settings_file, "r", encoding="utf-8") as f:
            existing_settings = json.load(f)
    except Exception:
        existing_settings = {}

if "assistant" not in existing_settings:
    existing_settings["assistant"] = {}

existing_settings["assistant"]["slash_commands"] = slash_commands_settings

with open(zed_settings_file, "w", encoding="utf-8", newline="\n") as f:
    json.dump(existing_settings, f, indent=2)

# 4. Create .zed/rules.md
zed_rules_file = os.path.join(ZED_DIR, "rules.md")
with open(zed_rules_file, "w", encoding="utf-8", newline="\n") as f:
    f.write("""# ACP Enhanced Instructions for Zed

This repository operates under the **Agent Context Protocol (ACP) Enhanced** framework.

## Context Loading Protocol
Before executing tasks or slash commands:
1. Always load and respect `AGENTS.md` (and `agent/core/identity.yml`, `agent/core/constraints.yml`).
2. When a slash command like `/acp-init`, `/acp-route`, `/acp-status`, or `/acp-commit` is used, execute the workflow specified in the corresponding `agent/commands/acp.*.md` document.
3. Follow the context budget and session memory commit protocol (`/acp-commit`).
""")

print(f"Generated {count} Zed Agent Skills in {SKILLS_DIR}")
print(f"Generated .zed/settings.json with {len(slash_commands_settings)} slash commands")
print(f"Generated .zed/rules.md")
