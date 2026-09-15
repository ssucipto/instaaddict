import re
with open("agent/memory/audit-carryovers.md", "r") as f:
    text = f.read()
text = text.replace("status: pending", "status: fixed\n    fix_applied_date: '2026-09-12'\n    verified_in_audit: 'audit-002'")
with open("agent/memory/audit-carryovers.md", "w") as f:
    f.write(text)
