with open("agent/memory/audit-carryovers.md", "a") as f:
    f.write("""
  - id: CO-002
    audit_report: agent/reports/audit-002-action-bar-failure.md
    date_raised: 2026-09-12
    severity: high
    status: pending
    summary: Fix action bar title lookup failure in views.py _getActionBarTitleBtn for IG v446
    affected_files:
      - InstaAddict/core/views.py
    fix_applied_date: null
    verified_in_audit: null
""")
