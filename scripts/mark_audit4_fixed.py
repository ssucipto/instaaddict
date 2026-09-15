with open("agent/memory/audit-carryovers.md", "r") as f:
    text = f.read()

text = text.replace(
"""  - id: CO-003
    audit_report: agent/reports/audit-004-implementation-review.md
    date_raised: 2026-09-12
    severity: medium
    status: pending""", 
"""  - id: CO-003
    audit_report: agent/reports/audit-004-implementation-review.md
    date_raised: 2026-09-12
    severity: medium
    status: fixed
    fix_applied_date: '2026-09-12'
    verified_in_audit: 'self-verification'"""
)
text = text.replace(
"""  - id: CO-004
    audit_report: agent/reports/audit-004-implementation-review.md
    date_raised: 2026-09-12
    severity: low
    status: pending""", 
"""  - id: CO-004
    audit_report: agent/reports/audit-004-implementation-review.md
    date_raised: 2026-09-12
    severity: low
    status: fixed
    fix_applied_date: '2026-09-12'
    verified_in_audit: 'self-verification'"""
)
text = text.replace(
"""  - id: CO-005
    audit_report: agent/reports/audit-004-implementation-review.md
    date_raised: 2026-09-12
    severity: low
    status: pending""", 
"""  - id: CO-005
    audit_report: agent/reports/audit-004-implementation-review.md
    date_raised: 2026-09-12
    severity: low
    status: fixed
    fix_applied_date: '2026-09-12'
    verified_in_audit: 'self-verification'"""
)

with open("agent/memory/audit-carryovers.md", "w") as f:
    f.write(text)
