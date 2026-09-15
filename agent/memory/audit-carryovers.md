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

  - id: CO-010
    audit_report: agent/reports/audit-023-reporting-and-error-tracing.md
    date_raised: 2026-09-13
    severity: high
    status: fixed
    fix_applied_date: '2026-09-13'
    verified_in_audit: 'audit-025'
    summary: Resolve Windows file lock leak, add total_crashes and upload tracking to SessionState, automate non-overwritten Markdown history on session completion, expand error logger to capture external errors and uncaught exceptions, and build automated dog-feeding analyzer.
    affected_files:
      - InstaAddict/core/log.py
      - InstaAddict/core/session_state.py
      - InstaAddict/core/report.py
      - InstaAddict/plugins/upload_posts.py
      - InstaAddict/plugins/data_analytics.py
      - InstaAddict/core/dogfood.py

  - id: CO-011
    audit_report: agent/reports/audit-027-ad-detection-and-browser-escape.md
    date_raised: 2026-09-13
    severity: critical
    status: fixed
    summary: Implement universal in-app browser watchdog/escape mechanism (BrowserLiteInMainProcessIGActivity) and modernize multi-vector ad detection across all interaction pipelines.
    affected_files:
      - InstaAddict/core/views.py
      - InstaAddict/core/handle_sources.py
      - InstaAddict/plugins/interact_reels.py
      - InstaAddict/core/resources.py

  - id: CO-012
    audit_report: agent/reports/audit-040-auto-upload-investigation.md
    date_raised: 2026-09-13
    severity: critical
    status: fixed
    fix_applied_date: 2026-09-14
    verified_in_audit: agent/reports/audit-042-auto-upload-verification.md
    summary: Resolve auto-upload non-functionality across case-sensitive file matching, silent failure exits, fragile username resolution, job scheduling limit abortion, missing .txt sidecars, and broken modern IG v446+ UI navigation via native ADD_TO_FEED intent sharing.
    affected_files:
      - InstaAddict/plugins/upload_posts.py
      - InstaAddict/core/bot_flow.py
      - InstaAddict/core/resources.py
      - InstaAddict/core/views.py
      - InstaAddict/core/utils.py
      - test/test_upload_posts.py

  - id: CO-013
    audit_report: agent/reports/audit-043-implementation-gaps-inconsistencies-shortcuts.md
    date_raised: 2026-09-14
    severity: high
    status: fixed
    fix_applied_date: 2026-09-14
    verified_in_audit: agent/reports/audit-044-remediation-verification.md
    summary: Address all 9 findings from Audit #043 and Review #034 including registering missing CLI arguments (--reels-topic, --upload-queue-dir), module globals initialization, shutil.move cross-device fixes, bare except remediation, modal regex expansion, and report upload metrics parity.
    affected_files:
      - InstaAddict/plugins/interact_reels.py
      - InstaAddict/plugins/upload_posts.py
      - InstaAddict/core/views.py
      - InstaAddict/core/interaction.py
      - InstaAddict/core/gemini_vision.py
      - InstaAddict/core/report.py
      - config-examples/config.yml
      - test/test_upload_posts.py
      - test/test_interact_reels.py

  - id: CO-014
    audit_report: agent/reports/audit-045-runtime-errors-and-locator-investigation.md
    date_raised: 2026-09-14
    severity: high
    status: fixed
    fix_applied_date: 2026-09-14
    verified_in_audit: route-043-remediation
    summary: Fix argument collision on --reels-topic and misleading error handling in config.py, handle EOFError in decorators.py, eliminate speculative profile check false-alarm errors, add modern tab bar resource IDs in resources.py and views.py, fix data analytics report path concatenation, and accelerate search recovery via action_bar_button_back.
    affected_files:
      - InstaAddict/plugins/core_arguments.py
      - InstaAddict/core/config.py
      - InstaAddict/core/decorators.py
      - InstaAddict/core/bot_flow.py
      - InstaAddict/core/views.py
      - InstaAddict/core/resources.py
      - InstaAddict/plugins/data_analytics.py

  - id: CO-015
    audit_report: agent/reports/audit-046-dual-implementation-remediation-audit.md
    date_raised: 2026-09-14
    severity: medium
    status: fixed
    fix_applied_date: 2026-09-14
    verified_in_audit: review-035-runtime-hardening-and-reels-navigation
    summary: Fix unguarded args.disable_filters in filter.py, differentiate KeyboardInterrupt from EOFError in bot_flow.py untested version prompt, enhance Reels like detection with get_selected and unlike regex in views.py, and expand test_runtime_hardening.py suite.
    affected_files:
      - InstaAddict/core/filter.py
      - InstaAddict/core/bot_flow.py
      - InstaAddict/core/views.py
      - test/test_runtime_hardening.py

  - id: CO-016
    audit_report: agent/reports/audit-048-upload-mechanism-gaps-and-shortcuts.md
    date_raised: 2026-09-14
    severity: high
    status: fixed
    fix_applied_date: '2026-09-14'
    verified_in_audit: review-036-upload-mechanism-code-quality.md
    summary: Remediate upload mechanism gaps including rate-limit mtime preservation, MediaStore ID resolution, ADB subprocess timeouts, unhandled upload exceptions, emoji caption typing fallback, device storage cleanup, and UTF-8-sig BOM handling.
    affected_files:
      - InstaAddict/plugins/upload_posts.py
      - test/test_upload_posts.py

