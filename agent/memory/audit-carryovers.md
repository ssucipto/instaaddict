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

  - id: CO-017
    audit_report: agent/reports/audit-054-profile-bot-infinite-photo-loop.md
    date_raised: 2026-09-16
    severity: critical
    status: fixed
    fix_applied_date: '2026-09-16'
    verified_in_audit: null
    summary: "F-01: Add device.back() after photo/carousel like in interact_with_user to mirror VIDEO branch and prevent infinite same-photo loop."
    affected_files:
      - InstaAddict/core/interaction.py

  - id: CO-018
    audit_report: agent/reports/audit-054-profile-bot-infinite-photo-loop.md
    date_raised: 2026-09-16
    severity: high
    status: fixed
    fix_applied_date: '2026-09-16'
    verified_in_audit: null
    summary: "F-04: Re-resolve row_view (not just post_view) on retry in navigateToPost to prevent stale RecyclerView child reference clicking same cell."
    affected_files:
      - InstaAddict/core/views.py

  - id: CO-019
    audit_report: agent/reports/audit-055-photo-upload-engagement-optimization.md
    date_raised: 2026-09-16
    severity: critical
    status: fixed
    fix_applied_date: '2026-09-16'
    verified_in_audit: 'self-verification'
    summary: "F-01: Missing `import time` in upload_posts.py — `time.sleep(1)` on line 217 causes NameError at runtime when HashtagManager retry fires."
    affected_files:
      - InstaAddict/plugins/upload_posts.py

  - id: CO-020
    audit_report: agent/reports/audit-055-photo-upload-engagement-optimization.md
    date_raised: 2026-09-16
    severity: high
    status: fixed
    fix_applied_date: '2026-09-16'
    verified_in_audit: 'self-verification'
    summary: "F-02: --upload-hashtags-in-comment argument declared but never consumed — implement first-comment hashtag posting after upload success."
    affected_files:
      - InstaAddict/plugins/upload_posts.py

  - id: CO-021
    audit_report: agent/reports/audit-055-photo-upload-engagement-optimization.md
    date_raised: 2026-09-16
    severity: high
    status: fixed
    fix_applied_date: '2026-09-16'
    verified_in_audit: 'self-verification'
    summary: "F-03: telegram_bot_send_text (lines 774,781) and telegram_bot_send_photo (line 832) have no HTTP timeout — can hang indefinitely, freezing the Telegram bot thread."
    affected_files:
      - InstaAddict/plugins/telegram.py

  - id: CO-022
    audit_report: agent/reports/audit-055-photo-upload-engagement-optimization.md
    date_raised: 2026-09-16
    severity: high
    status: fixed
    fix_applied_date: '2026-09-16'
    verified_in_audit: 'self-verification'
    summary: "F-04: Upload success verification uses only 8-12s fixed sleep + single Home tab check — replace with active polling loop (30s max, 3s intervals)."
    affected_files:
      - InstaAddict/plugins/upload_posts.py

  - id: CO-023
    audit_report: agent/reports/audit-055-photo-upload-engagement-optimization.md
    date_raised: 2026-09-16
    severity: high
    status: fixed
    fix_applied_date: '2026-09-16'
    verified_in_audit: 'self-verification'
    summary: "F-05: Gemini model name 'gemini-3.6-flash' verified valid for 2026 API catalog."
    affected_files:
      - InstaAddict/core/gemini_vision.py

  - id: CO-024
    audit_report: agent/reports/audit-055-photo-upload-engagement-optimization.md
    date_raised: 2026-09-16
    severity: medium
    status: fixed
    fix_applied_date: '2026-09-16'
    verified_in_audit: 'self-verification'
    summary: "F-06/F-11: /preview sends text-only for video; upload success notification sends text only — implement sendVideo for preview and photo thumbnail in success notification."
    affected_files:
      - InstaAddict/plugins/telegram.py

  - id: CO-025
    audit_report: agent/reports/audit-055-photo-upload-engagement-optimization.md
    date_raised: 2026-09-16
    severity: medium
    status: fixed
    fix_applied_date: '2026-09-16'
    verified_in_audit: 'self-verification'
    summary: "F-08/F-14: Hard-coded fallback hashtags (jackrussell/perthdogs) should be configurable via YAML; /queue sort order should match mtime posting order."
    affected_files:
      - InstaAddict/plugins/upload_posts.py
      - InstaAddict/plugins/telegram.py

  - id: CO-026
    audit_report: agent/reports/audit-055-photo-upload-engagement-optimization.md
    date_raised: 2026-09-16
    severity: medium
    status: fixed
    fix_applied_date: '2026-09-16'
    verified_in_audit: 'self-verification'
    summary: "F-10/F-15: Caption AI prompt lacks engagement hooks (questions/CTAs); no max_output_tokens cap (risk of 2200-char Instagram limit violation)."
    affected_files:
      - InstaAddict/core/gemini_vision.py

  - id: CO-027
    audit_report: agent/reports/audit-055-photo-upload-engagement-optimization.md
    date_raised: 2026-09-16
    severity: low
    status: fixed
    fix_applied_date: '2026-09-16'
    verified_in_audit: 'self-verification'
    summary: "F-09/F-13: MEDIA_SCANNER_SCAN_FILE broadcast deprecated on Android 10+; trigger_on_demand_upload subprocess ignores custom --upload-queue-dir."
    affected_files:
      - InstaAddict/plugins/upload_posts.py
      - InstaAddict/plugins/telegram.py

  - id: CO-028
    audit_report: agent/reports/audit-056-instagram-popups-and-stuck-screen-resilience.md
    date_raised: 2026-09-16
    severity: critical
    status: fixed
    fix_applied_date: '2026-09-16'
    verified_in_audit: 'audit-057'
    summary: "F-01: Universal dialog dismissal engine in UniversalActions (Rate Instagram 'No, thanks', notifications 'Not now', stacked popups)."
    affected_files:
      - InstaAddict/core/views.py

  - id: CO-029
    audit_report: agent/reports/audit-056-instagram-popups-and-stuck-screen-resilience.md
    date_raised: 2026-09-16
    severity: critical
    status: fixed
    fix_applied_date: '2026-09-16'
    verified_in_audit: 'audit-057'
    summary: "F-02: Post-upload dialog sweep in upload_posts.py to clear post-upload dialogs before returning."
    affected_files:
      - InstaAddict/plugins/upload_posts.py

  - id: CO-030
    audit_report: agent/reports/audit-056-instagram-popups-and-stuck-screen-resilience.md
    date_raised: 2026-09-16
    severity: critical
    status: fixed
    fix_applied_date: '2026-09-16'
    verified_in_audit: 'audit-057'
    summary: "F-03: Hardened inter-job recovery loop in bot_flow.py to avoid spurious recovered=True when dialog overlays tab bar."
    affected_files:
      - InstaAddict/core/bot_flow.py

  - id: CO-031
    audit_report: agent/reports/audit-056-instagram-popups-and-stuck-screen-resilience.md
    date_raised: 2026-09-16
    severity: high
    status: fixed
    fix_applied_date: '2026-09-16'
    verified_in_audit: 'audit-057'
    summary: "F-04: Multi-attempt retry before skipping jobs in bot_flow.py."
    affected_files:
      - InstaAddict/core/bot_flow.py

  - id: CO-032
    audit_report: agent/reports/audit-056-instagram-popups-and-stuck-screen-resilience.md
    date_raised: 2026-09-16
    severity: high
    status: fixed
    fix_applied_date: '2026-09-16'
    verified_in_audit: 'audit-057'
    summary: "F-05: TabBarView._navigateTo fallback to dialog dismissal and back press on missing tab button."
    affected_files:
      - InstaAddict/core/views.py

  - id: CO-033
    audit_report: agent/reports/audit-056-instagram-popups-and-stuck-screen-resilience.md
    date_raised: 2026-09-16
    severity: high
    status: fixed
    fix_applied_date: '2026-09-16'
    verified_in_audit: 'audit-057'
    summary: "F-06/F-07: Escalated stuck-screen recovery with clean app relaunch (app_stop + app_start) in UniversalActions and bot_flow.py."
    affected_files:
      - InstaAddict/core/views.py
      - InstaAddict/core/bot_flow.py

  - id: CO-034
    audit_report: agent/reports/audit-058-security-integrity-privacy-review.md
    date_raised: 2026-09-16
    severity: high
    status: fixed
    fix_applied_date: '2026-09-16'
    verified_in_audit: 'self-verification'
    summary: "SEC-01: Decoupled hardcoded persona strings and regional hashtags from core modules into generic creator defaults."
    affected_files:
      - InstaAddict/core/gemini_vision.py
      - InstaAddict/core/hashtag_manager.py
      - InstaAddict/plugins/upload_posts.py
      - scripts/check_telegram.py

  - id: CO-035
    audit_report: agent/reports/audit-058-security-integrity-privacy-review.md
    date_raised: 2026-09-16
    severity: critical
    status: fixed
    fix_applied_date: '2026-09-16'
    verified_in_audit: 'self-verification'
    summary: "SEC-02: Eliminated shell=True from ADB and system calls across core/utils.py and device_facade.py (OWASP A03:2021 Injection defense)."
    affected_files:
      - InstaAddict/core/utils.py
      - InstaAddict/core/device_facade.py

  - id: CO-036
    audit_report: agent/reports/audit-058-security-integrity-privacy-review.md
    date_raised: 2026-09-16
    severity: high
    status: fixed
    fix_applied_date: '2026-09-16'
    verified_in_audit: 'self-verification'
    summary: "SEC-03: Auto-detect single configured account in scripts/check_telegram.py and remove hardcoded username defaults."
    affected_files:
      - scripts/check_telegram.py

  - id: CO-037
    audit_report: agent/reports/audit-059-security-privacy-git-history-exposure.md
    date_raised: 2026-09-17
    severity: critical
    status: pending
    fix_applied_date: null
    verified_in_audit: null
    summary: "SEC-H1/H2/H3: Live Telegram bot token (8633425071:AAFm...), chat ID (-5156789010), and real Instagram usernames (_joakim.__, _joeahkim, kashbettingtip) are in public git history (commits bf191976, 15698e99, c20b98a). Token must be REVOKED and git history must be rewritten with git filter-repo."
    affected_files:
      - .git history (accounts/ paths in commits bf191976, 15698e99, c20b98a, 4a3059e, bf86e3d)

  - id: CO-038
    audit_report: agent/reports/audit-059-security-privacy-git-history-exposure.md
    date_raised: 2026-09-17
    severity: high
    status: pending
    fix_applied_date: null
    verified_in_audit: null
    summary: "SEC-H4/H5: Entire .venv/ and gramaddict-joeahkim/.venv/ committed in git history — massive bloat and supply-chain provenance risk. Must be purged via git filter-repo."
    affected_files:
      - .git history (.venv/ paths in commits bf191976, 15698e99)

  - id: CO-039
    audit_report: agent/reports/audit-059-security-privacy-git-history-exposure.md
    date_raised: 2026-09-17
    severity: high
    status: pending
    fix_applied_date: null
    verified_in_audit: null
    summary: "SEC-M1: Personal Perth/JRT hashtags still hardcoded in hashtag_manager.py fallback default template (perthdogs, dogsofperth, jackrussell, jrt at lines 128-136) and FALLBACK_TAGS constant (jackrussell, wa, australia at lines 45-58). Replace with generic non-identifying tags."
    affected_files:
      - InstaAddict/core/hashtag_manager.py

  - id: CO-040
    audit_report: agent/reports/audit-059-security-privacy-git-history-exposure.md
    date_raised: 2026-09-17
    severity: medium
    status: pending
    fix_applied_date: null
    verified_in_audit: null
    summary: "SEC-M2/M3: Attribution strings in utils.py (lines 74, 91, 98) and config guide URLs in __main__.py (lines 16, 23) and bot_flow.py (line 73) still reference joeahkim/InstaAddict. Update to ssucipto/instaaddict."
    affected_files:
      - InstaAddict/core/utils.py
      - InstaAddict/__main__.py
      - InstaAddict/core/bot_flow.py

  - id: CO-041
    audit_report: agent/reports/audit-059-security-privacy-git-history-exposure.md
    date_raised: 2026-09-17
    severity: medium
    status: pending
    fix_applied_date: null
    verified_in_audit: null
    summary: "SEC-L2/L3: ai_comment_history.json, current_screen.xml, dump_screen.xml, window.xml, out.txt, data_analytics_old.py tracked in git — session fingerprints and device dumps. Remove from tracking via git rm --cached and update .gitignore."
    affected_files:
      - ai_comment_history.json
      - current_screen.xml
      - dump_screen.xml
      - window.xml
      - out.txt
      - data_analytics_old.py
      - .gitignore

  - id: CO-042
    audit_report: agent/reports/audit-059-security-privacy-git-history-exposure.md
    date_raised: 2026-09-17
    severity: medium
    status: pending
    fix_applied_date: null
    verified_in_audit: null
    summary: "SEC-L1: One-time helper scripts in scripts/ contain personal hashtags (jackrussell, dogsofinstagram in revert_hashtag_yaml.py:7, patch_optimal_config.py:25, generate_docx.py:41). Sanitize or remove these scripts."
    affected_files:
      - scripts/revert_hashtag_yaml.py
      - scripts/patch_optimal_config.py
      - scripts/generate_docx.py
