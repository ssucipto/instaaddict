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

  - id: CO-006
    audit_report: agent/reports/audit-015-swipe-distance-snapback.md
    date_raised: 2026-09-13
    severity: high
    status: fixed
    fix_applied_date: '2026-09-13'
    verified_in_audit: 'self-verification'
    summary: Hardcoded pixel defaults in UniversalActions._swipe_points and scattered micro-scrolls cause snap-backs on modern IG layouts
    affected_files:
      - InstaAddict/core/views.py
      - InstaAddict/core/interaction.py

  - id: CO-007
    audit_report: agent/reports/audit-015-swipe-distance-snapback.md
    date_raised: 2026-09-13
    severity: medium
    status: fixed
    fix_applied_date: '2026-09-13'
    verified_in_audit: 'self-verification'
    summary: swipe_points uses drag instead of swipe, lacking fling momentum necessary for Reels-like feed navigation
    affected_files:
      - InstaAddict/core/device_facade.py

  - id: CO-008
    audit_report: agent/reports/audit-018-vision-ai-quota.md
    date_raised: 2026-09-13
    severity: critical
    status: fixed
    fix_applied_date: '2026-09-13'
    verified_in_audit: 'self-verification'
    summary: Vision AI calls use raw 1080p images on every reel without resizing, duplicate screenshots for commenting, and flawed Optical Hashing resulting in severe quota burn.
    affected_files:
      - InstaAddict/core/gemini_vision.py
      - InstaAddict/plugins/interact_reels.py

  - id: CO-009
    audit_report: agent/reports/audit-019-upstream-commits.md
    date_raised: 2026-09-13
    severity: medium
    status: fixed
    fix_applied_date: '2026-09-13'
    verified_in_audit: 'audit-020'
    summary: Upstream repository has 5 relevant UI bugfix commits. Need to safely cherry-pick them to avoid "merge conflicts" and preserve custom Vision AI/Uploader logic.
    affected_files:
      - InstaAddict/core/bot_flow.py
      - InstaAddict/core/interaction.py
      - InstaAddict/core/views.py
      - InstaAddict/core/handle_sources.py
