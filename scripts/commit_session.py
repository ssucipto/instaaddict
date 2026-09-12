import os
from datetime import datetime
import yaml

sessions_file = 'agent/memory/sessions.md'
with open(sessions_file, 'r', encoding='utf-8') as f:
    content = f.read()

new_session = """
- date: 2026-09-12
  executor: Antigravity
  branch: master
  tasks_completed: [task-17, task-18, task-19]
  done:
    - fixed-yaml-arguments-in-uploader
    - resolved-argparse-metavar-crash
    - silenced-google-sdk-deprecation-warnings
    - successfully-validated-project-and-completed-m6
  deferred: []
  key_fact: "M6 Autopilot Uploads & Vision UI fully architected and stabilized. configargparse natively chokes on nested dicts without metavars or string-wrapped spaces; always use explicit widths or quotes when hacking user YAMLs."
"""

code = content + new_session

with open(sessions_file, 'w', encoding='utf-8') as f:
    f.write(code)

os.makedirs('agent/sessions', exist_ok=True)
md_content = """# Session: 2026-09-12

**Executor**: Antigravity
**Branch**: master
**Tasks**: [task-17, task-18, task-19]

## Completed
- fixed-yaml-arguments-in-uploader
- resolved-argparse-metavar-crash
- silenced-google-sdk-deprecation-warnings
- successfully-validated-project-and-completed-m6

## Deferred
None

## Key Fact
M6 Autopilot Uploads & Vision UI fully architected and stabilized. configargparse natively chokes on nested dicts without metavars or string-wrapped spaces; always use explicit widths or quotes when hacking user YAMLs.
"""

with open('agent/sessions/2026-09-12-fixed-yaml-arguments.md', 'w', encoding='utf-8') as f:
    f.write(md_content)
