with open("agent/memory/audit-carryovers.md", "a") as f:
    f.write("""
  - id: CO-003
    audit_report: agent/reports/audit-004-implementation-review.md
    date_raised: 2026-09-12
    severity: medium
    status: pending
    summary: Missing Task 8 (establish post publishing pipeline) in progress tracking
    affected_files:
      - agent/progress.yaml
      - agent/tasks/milestone-2-compatibility/task-8-establish-post-pipeline.md
    fix_applied_date: null
    verified_in_audit: null

  - id: CO-004
    audit_report: agent/reports/audit-004-implementation-review.md
    date_raised: 2026-09-12
    severity: low
    status: pending
    summary: Bare exception handling shortcut in views.py _get_media_container
    affected_files:
      - InstaAddict/core/views.py
    fix_applied_date: null
    verified_in_audit: null

  - id: CO-005
    audit_report: agent/reports/audit-004-implementation-review.md
    date_raised: 2026-09-12
    severity: low
    status: pending
    summary: Hardcoded time.sleep(2) shortcut in views.py changeToUsername
    affected_files:
      - InstaAddict/core/views.py
    fix_applied_date: null
    verified_in_audit: null
""")
