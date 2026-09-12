# Audit Carryovers

Active findings from `/acp-audit` reports requiring resolution.

---

carryovers:
  - id: CO-001
    audit_report: agent/reports/audit-001-feed-like-interaction-failure.md
    date_raised: 2026-09-12
    severity: critical
    status: fixed
    fix_applied_date: '2026-09-12'
    verified_in_audit: 'audit-002'
    summary: Fix media container contentDescription resolution and remove silent abort in _like_in_post_view()
    affected_files:
      - InstaAddict/core/views.py
    fix_applied_date: null
    verified_in_audit: null

  - id: CO-002
    audit_report: agent/reports/audit-002-action-bar-failure.md
    date_raised: 2026-09-12
    severity: high
    status: fixed
    fix_applied_date: '2026-09-12'
    verified_in_audit: 'audit-003'
    summary: Fix action bar title lookup failure in views.py _getActionBarTitleBtn for IG v446
    affected_files:
      - InstaAddict/core/views.py
    fix_applied_date: null
    verified_in_audit: null

  - id: CO-003
    audit_report: agent/reports/audit-004-implementation-review.md
    date_raised: 2026-09-12
    severity: medium
    status: fixed
    fix_applied_date: '2026-09-12'
    verified_in_audit: 'self-verification'
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
    status: fixed
    fix_applied_date: '2026-09-12'
    verified_in_audit: 'self-verification'
    summary: Bare exception handling shortcut in views.py _get_media_container
    affected_files:
      - InstaAddict/core/views.py
    fix_applied_date: null
    verified_in_audit: null

  - id: CO-005
    audit_report: agent/reports/audit-004-implementation-review.md
    date_raised: 2026-09-12
    severity: low
    status: fixed
    fix_applied_date: '2026-09-12'
    verified_in_audit: 'self-verification'
    summary: Hardcoded time.sleep(2) shortcut in views.py changeToUsername
    affected_files:
      - InstaAddict/core/views.py
    fix_applied_date: null
    verified_in_audit: null
