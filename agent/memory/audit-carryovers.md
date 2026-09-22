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
    status: fixed
    fix_applied_date: '2026-09-17'
    verified_in_audit: 'audit-059-post-impl'
    summary: "SEC-H1/H2/H3: Historical credentials and personal account paths were in early upstream git history. accounts/ paths completely purged from git history via git filter-repo and forced-pushed to origin."
    affected_files:
      - .git history (accounts/ paths purged from all history)

  - id: CO-038
    audit_report: agent/reports/audit-059-security-privacy-git-history-exposure.md
    date_raised: 2026-09-17
    severity: high
    status: fixed
    fix_applied_date: '2026-09-17'
    verified_in_audit: 'audit-059-post-impl'
    summary: "SEC-H4/H5: Entire .venv/ and gramaddict-joeahkim/.venv/ committed in git history — purged via git filter-repo."
    affected_files:
      - .git history (.venv/ and gramaddict-*/ paths purged)

  - id: CO-039
    audit_report: agent/reports/audit-059-security-privacy-git-history-exposure.md
    date_raised: 2026-09-17
    severity: high
    status: fixed
    fix_applied_date: '2026-09-17'
    verified_in_audit: 'audit-059-post-impl'
    summary: "SEC-M1: Personal hashtags purged from hashtag_manager.py fallback default template and FALLBACK_TAGS constant. Replaced with generic non-identifying tags."
    affected_files:
      - InstaAddict/core/hashtag_manager.py

  - id: CO-040
    audit_report: agent/reports/audit-059-security-privacy-git-history-exposure.md
    date_raised: 2026-09-17
    severity: medium
    status: fixed
    fix_applied_date: '2026-09-17'
    verified_in_audit: 'audit-059-post-impl'
    summary: "SEC-M2/M3: Attribution strings and config guide URLs in utils.py, __main__.py, and bot_flow.py updated to point to ssucipto/instaaddict."
    affected_files:
      - InstaAddict/core/utils.py
      - InstaAddict/__main__.py
      - InstaAddict/core/bot_flow.py

  - id: CO-041
    audit_report: agent/reports/audit-059-security-privacy-git-history-exposure.md
    date_raised: 2026-09-17
    severity: medium
    status: fixed
    fix_applied_date: '2026-09-17'
    verified_in_audit: 'audit-059-post-impl'
    summary: "SEC-L2/L3: ai_comment_history.json, current_screen.xml, dump_screen.xml, window.xml, out.txt, data_analytics_old.py untracked from git and ignored in .gitignore."
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
    status: fixed
    fix_applied_date: '2026-09-17'
    verified_in_audit: 'audit-059-post-impl'
    summary: "SEC-L1: Helper scripts in scripts/ sanitized of personal tags and personas."
    affected_files:
      - scripts/revert_hashtag_yaml.py
      - scripts/patch_optimal_config.py
      - scripts/generate_docx.py
      - scripts/set_persona.py
      - scripts/set_correct_persona.py
      - scripts/quote_yaml.py
      - scripts/patch_universal_persona.py

  - id: CO-043
    audit_report: agent/reports/audit-060-tui-implementation-gaps-and-code-quality.md
    date_raised: 2026-09-17
    severity: critical
    status: fixed
    fix_applied_date: '2026-09-17'
    verified_in_audit: 'self-verification'
    summary: "Windows CP1252/CP437 UnicodeEncodeError on raw emoji glyphs in rich Console. Added safe_glyph() and safe_box=True."
    affected_files:
      - InstaAddict/core/tui.py

  - id: CO-044
    audit_report: agent/reports/audit-060-tui-implementation-gaps-and-code-quality.md
    date_raised: 2026-09-17
    severity: high
    status: fixed
    fix_applied_date: '2026-09-17'
    verified_in_audit: 'self-verification'
    summary: "Missing atexit and signal terminal restoration guards. Registered atexit.register(self.stop) and countdown try-finally."
    affected_files:
      - InstaAddict/core/tui.py
      - InstaAddict/core/utils.py

  - id: CO-045
    audit_report: agent/reports/audit-060-tui-implementation-gaps-and-code-quality.md
    date_raised: 2026-09-17
    severity: medium
    status: fixed
    fix_applied_date: '2026-09-17'
    verified_in_audit: 'self-verification'
    summary: "Nullable limits in SessionState throwing TypeError in int() aborting remaining limits. Added _safe_int() helper."
    affected_files:
      - InstaAddict/core/tui.py

  - id: CO-046
    audit_report: agent/reports/audit-060-tui-implementation-gaps-and-code-quality.md
    date_raised: 2026-09-17
    severity: medium
    status: fixed
    fix_applied_date: '2026-09-17'
    verified_in_audit: 'self-verification'
    summary: "Multiline log records and long lines distorting TUI panel formatting. Added splitlines() and line length cap."
    affected_files:
      - InstaAddict/core/tui.py

  - id: CO-047
    audit_report: agent/reports/audit-060-tui-implementation-gaps-and-code-quality.md
    date_raised: 2026-09-17
    severity: medium
    status: fixed
    fix_applied_date: '2026-09-17'
    verified_in_audit: 'self-verification'
    summary: "Narrow terminal width (< 85 cols) squishing dual-column layout. Added responsive single-column layout fallback."
    affected_files:
      - InstaAddict/core/tui.py

  - id: CO-048
    audit_report: agent/reports/audit-060-tui-implementation-gaps-and-code-quality.md
    date_raised: 2026-09-17
    severity: low
    status: fixed
    fix_applied_date: '2026-09-17'
    verified_in_audit: 'self-verification'
    summary: "agent/progress.yaml project status not reset to completed post-M10. Set project.status to completed and current_milestone to null."
    affected_files:
      - agent/progress.yaml

  - id: CO-049
    audit_report: agent/reports/audit-061-tui-flickering-root-cause-analysis-and-fix.md
    date_raised: 2026-09-17
    severity: high
    status: fixed
    fix_applied_date: '2026-09-17'
    verified_in_audit: 'self-verification'
    summary: "Terminal interface flickering eliminated by implementing screen=True alternate buffer, vertical_overflow=crop, safe_glyph CP1252/CP437 sanitization, bounded logs slicing, and 1.5 Hz rate-limited rendering."
    affected_files:
      - InstaAddict/core/tui.py
      - test/test_tui_dashboard.py

  - id: CO-050
    audit_report: agent/reports/audit-063-codebase-gaps-bare-excepts-and-quality-hardening.md
    date_raised: 2026-09-18
    severity: high
    status: fixed
    fix_applied_date: '2026-09-18'
    verified_in_audit: agent/reports/audit-064-post-implementation-verification-and-remediation.md
    summary: "Remediated 10 audit findings across core and tests: replaced bare except: blocks in interaction.py and download_from_github.py, added explicit timeout=5 and module-level import for subprocess in interaction.py, removed unused imports across bot_flow.py, gemini_vision.py, tui.py, test_tui_dashboard.py, test_runtime_hardening.py, and test_unicode_sanitizer.py, and preserved random_sleep test-mock compatibility in filter.py."
    affected_files:
      - InstaAddict/core/interaction.py
      - InstaAddict/core/download_from_github.py
      - InstaAddict/core/bot_flow.py
      - InstaAddict/core/filter.py
      - InstaAddict/core/gemini_vision.py
      - InstaAddict/core/tui.py
      - test/test_tui_dashboard.py
      - test/test_runtime_hardening.py
      - test/test_unicode_sanitizer.py

  - id: CO-051
    audit_report: agent/reports/audit-065-tui-live-effort-counters-and-queue-management.md
    date_raised: 2026-09-18
    severity: high
    status: fixed
    fix_applied_date: '2026-09-18'
    verified_in_audit: agent/reports/audit-066-terminal-interface-effort-counters-and-queue-management.md
    summary: "TUI static stats illusion resolved by implementing real-time operational effort counters (posts scanned, profiles checked/skipped with pass rate %, ads bypassed, dialogs dismissed, reels evaluated), live execution context hook-up in hot paths, content queue telemetry engine, and cross-platform non-blocking keyboard listener for [U] on-demand queue photo upload."
    affected_files:
      - InstaAddict/core/session_state.py
      - InstaAddict/core/tui.py
      - InstaAddict/core/handle_sources.py
      - InstaAddict/core/filter.py
      - InstaAddict/plugins/interact_reels.py
      - InstaAddict/core/views.py
      - InstaAddict/core/bot_flow.py
      - test/test_tui_dashboard.py

  - id: CO-052
    audit_report: agent/reports/audit-067-peek-preview-interaction-and-profile-navigation-hang.md
    date_raised: 2026-09-18
    severity: high
    status: fixed
    fix_applied_date: '2026-09-18'
    verified_in_audit: agent/reports/audit-068-peek-preview-and-profile-navigation-verification.md
    summary: "Eliminated Peek Preview stagnation and single-profile navigation hang by implementing in-preview like action execution (effort not wasted), fast coordinate tapping to evade long-press listeners, a 2-failure circuit breaker to abort stuck profiles, and a verified profile exit loop in handle_sources.py."
    affected_files:
      - InstaAddict/core/views.py
      - InstaAddict/core/interaction.py
      - InstaAddict/core/handle_sources.py
      - test/test_runtime_hardening.py

  - id: CO-053
    audit_report: agent/reports/audit-069-zero-metrics-likers-container-and-engagement-starvation.md
    date_raised: 2026-09-18
    severity: critical
    status: fixed
    fix_applied_date: '2026-09-18'
    verified_in_audit: agent/reports/audit-070-engagement-metrics-and-reels-deadlock-verification.md
    summary: "Eliminated 0% session metrics starvation and Reels rejection deadlock by replacing (True, 0) likers container return with (False, -1) in PostsViewList._find_likers_container, synchronizing totalWatched, totalLikes, and add_interaction in interact_reels.py, injecting dynamic current_user for comment verification, recording feed interactions in handle_sources.py, and fixing SessionState add_interaction successfulInteractions overwrite bug."
    affected_files:
      - InstaAddict/core/views.py
      - InstaAddict/plugins/interact_reels.py
      - InstaAddict/core/handle_sources.py
      - InstaAddict/core/session_state.py
      - test/test_runtime_hardening.py
      - test/test_interact_reels.py

  - id: CO-054
    audit_report: agent/reports/audit-071-task-skip-shortcut-and-navigation.md
    date_raised: 2026-09-18
    severity: medium
    status: fixed
    fix_applied_date: '2026-09-18'
    verified_in_audit: agent/reports/audit-071-task-skip-shortcut-and-navigation.md
    summary: "Implemented interactive Task Skip Shortcut ([S]/[N]) and IPC signal file (.skip_task) allowing operators to immediately skip the currently executing task/job/source and advance cleanly to the next scheduled task. Hooked into countdown(), bot_flow.py, handle_sources.py (handle_posts, handle_likers, handle_blogger), interact_reels.py, and action_unfollow_followers.py with visual TUI status feedback."
    affected_files:
      - InstaAddict/core/tui.py
      - InstaAddict/core/utils.py
      - InstaAddict/core/bot_flow.py
      - InstaAddict/core/handle_sources.py
      - InstaAddict/plugins/interact_reels.py
      - InstaAddict/plugins/action_unfollow_followers.py
      - InstaAddict/core/interaction.py
      - test/test_tui_dashboard.py
      - test/test_runtime_hardening.py

  - id: CO-055
    audit_report: agent/reports/audit-072-telegram-inbox-operation-type-error-and-tui-crash.md
    date_raised: 2026-09-18
    severity: critical
    status: fixed
    fix_applied_date: '2026-09-18'
    verified_in_audit: agent/reports/audit-072-telegram-inbox-operation-type-error-and-tui-crash.md
    summary: "Resolved fatal TypeError in TelegramReports.run() and invisible console crash under active TUI. Removed operation: True from --telegram-inbox, added defensive signature handling in TelegramReports.run(), stripped telegram-inbox from jobs_list in bot_flow.py, and ensured handle_uncaught_exception tears down DashboardManager and dispatches to sys.__excepthook__."
    affected_files:
      - InstaAddict/plugins/telegram.py
      - InstaAddict/core/bot_flow.py
      - InstaAddict/core/log.py
      - test/test_telegram_inbox.py

  - id: CO-056
    audit_report: agent/reports/audit-075-self-healing-recovery-and-watchdog-resilience.md
    date_raised: 2026-09-18
    severity: critical
    status: fixed
    fix_applied_date: '2026-09-19'
    verified_in_audit: 'audit-077'
    summary: "Fix BotWatchdog escalation timer reset bug in _execute_soft_recovery where resetting self.last_heartbeat = time.time() prevents the watchdog from ever escalating from Tier 1 to Tier 2 (task skip) and Tier 3 (nuclear app relaunch) during persistent hangs."
    affected_files:
      - InstaAddict/core/watchdog.py
      - test/test_watchdog.py

  - id: CO-057
    audit_report: agent/reports/audit-075-self-healing-recovery-and-watchdog-resilience.md
    date_raised: 2026-09-18
    severity: high
    status: fixed
    fix_applied_date: '2026-09-19'
    verified_in_audit: 'audit-077'
    summary: "Instrument granular heartbeat emission across countdown(), DashboardState.update_activity(), interact_reels, handle_sources, and upload_posts to prevent false-positive watchdog stall triggers during long healthy operations exceeding 90 seconds."
    affected_files:
      - InstaAddict/core/utils.py
      - InstaAddict/core/tui.py
      - InstaAddict/core/handle_sources.py
      - InstaAddict/plugins/interact_reels.py
      - InstaAddict/plugins/upload_posts.py
      - test/test_watchdog.py

  - id: CO-058
    audit_report: agent/reports/audit-076-tcl-asyncdelete-wrong-thread-and-matplotlib-backend.md
    date_raised: 2026-09-19
    severity: critical
    status: fixed
    fix_applied_date: '2026-09-19'
    verified_in_audit: 'self-verification'
    summary: "Eliminate Tcl_AsyncDelete fatal thread crash by forcing non-GUI Agg backend for matplotlib, setting MPLBACKEND=Agg at process entrypoints, guarding optional dependencies, and isolating pyplot from multithreaded teardown."
    affected_files:
      - run.py
      - InstaAddict/__init__.py
      - InstaAddict/__main__.py
      - InstaAddict/plugins/data_analytics.py
      - test/test_matplotlib_backend.py

  - id: CO-059
    audit_report: agent/reports/audit-077-follows-unfollows-comments-zero-metrics-investigation.md
    date_raised: 2026-09-19
    severity: critical
    status: fixed
    fix_applied_date: '2026-09-19'
    verified_in_audit: 'audit-078'
    summary: "Resolve zero follows metric by removing strict clickable=True constraint on TextView nodes in ProfileView.getFollowButton() and interaction._follow(), preventing profiles from being falsely dropped with SkipReason.NOT_LOADED in Filter.check_profile()."
    affected_files:
      - InstaAddict/core/views.py
      - InstaAddict/core/interaction.py
      - InstaAddict/core/filter.py

  - id: CO-060
    audit_report: agent/reports/audit-077-follows-unfollows-comments-zero-metrics-investigation.md
    date_raised: 2026-09-19
    severity: critical
    status: fixed
    fix_applied_date: '2026-09-19'
    verified_in_audit: 'audit-078'
    summary: "Resolve zero comments metric by preventing destructive downward swipe on MediaType.REEL in _comment(), adding multi-tier comment button locators for Reels, implementing robust multi-tier comment post verification, and providing safe fallback comments."
    affected_files:
      - InstaAddict/core/interaction.py
      - InstaAddict/plugins/interact_reels.py

  - id: CO-061
    audit_report: agent/reports/audit-077-follows-unfollows-comments-zero-metrics-investigation.md
    date_raised: 2026-09-19
    severity: critical
    status: fixed
    fix_applied_date: '2026-09-19'
    verified_in_audit: 'audit-078'
    summary: "Resolve zero unfollows metric by ensuring ProfileView.navigateToFollowing() returns True when the following list opens directly, replacing rigid child index traversal in user list iteration with resilient element discovery, and supporting multi-tier unfollow confirmation locators."
    affected_files:
      - InstaAddict/core/views.py
      - InstaAddict/plugins/action_unfollow_followers.py

  - id: CO-062
    audit_report: agent/reports/audit-101-ctrl-s-task-skipping-and-visual-feedback.md
    date_raised: 2026-09-20
    severity: medium
    status: fixed
    fix_applied_date: '2026-09-20'
    verified_in_audit: agent/reports/audit-101-ctrl-s-task-skipping-and-visual-feedback.md
    summary: "Hardened Windows console mode to clear ENABLE_PROCESSED_INPUT on CONIN$, promoted single-key shortcuts [S]/[N] to prevent conhost XOFF and IDE key intercept, added full Job Queue Pipeline visualization in TUI activity panel, and clarified Level 2 Task Type skip semantics."
    affected_files:
      - InstaAddict/core/tui.py
      - InstaAddict/core/bot_flow.py
      - test/test_tui_dashboard.py

  - id: CO-063
    audit_report: agent/reports/audit-103-pre-implementation-tuning-gaps-and-hardening.md
    date_raised: 2026-09-20
    severity: high
    status: fixed
    fix_applied_date: '2026-09-20'
    verified_in_audit: agent/reports/audit-104-operational-hardening-verification.md
    summary: "Add defensive EmptyList exception handling in views.py:3129 (harvest_visible_followers) and handle_sources.py:455 (handle_likers), update @lolatheozjack configuration to eliminate business-profile starvation (skip_business: false), adjust AI evaluation quota (evaluate-percentage: 20), and expand blogger rotation list."
    affected_files:
      - InstaAddict/core/views.py
      - InstaAddict/core/handle_sources.py
      - accounts/lolatheozjack/filters.yml
      - accounts/lolatheozjack/config.yml

  - id: CO-064
    audit_report: agent/reports/audit-111-early-session-termination-and-watchdog-race.md
    date_raised: 2026-09-22
    severity: critical
    status: fixed
    fix_applied_date: '2026-09-22'
    verified_in_audit: agent/reports/audit-111-early-session-termination-and-watchdog-race.md
    summary: "Resolve early session termination and drop to shell prompt caused by BotWatchdog 90s inactivity timeout triggering Tier 1 KEYCODE_BACK recovery during emulator cold launch, displacing Instagram from Profile to Home feed and causing getProfileInfo() to return None which bot_flow.py misclassified as an account soft-ban."
    affected_files:
      - InstaAddict/core/utils.py
      - InstaAddict/core/views.py
      - InstaAddict/core/bot_flow.py
      - test/test_tuning_and_operational_fixes.py

  - id: CO-065
    audit_report: agent/reports/audit-112-anr-app-has-crashed-and-startup-retry-resilience.md
    date_raised: 2026-09-22
    severity: critical
    status: fixed
    fix_applied_date: '2026-09-22'
    verified_in_audit: agent/reports/audit-112-anr-app-has-crashed-and-startup-retry-resilience.md
    summary: "Harden bot against AppHasCrashed during ProfileView/ActionBarView initialization after sleep wake-up by safely initializing action_bar in try/except AppHasCrashed, verifying foreground status at open_instagram conclusion, emitting watchdog heartbeats when tapping Wait on Android system ANR dialogs, guarding choose_cloned_app against None configs/ResourceID, and wrapping startup profile initialization in a 3-attempt self-healing retry loop in start_bot()."
    affected_files:
      - InstaAddict/core/views.py
      - InstaAddict/core/utils.py
      - InstaAddict/core/bot_flow.py
      - test/test_tuning_and_operational_fixes.py

  - id: CO-066
    audit_report: agent/reports/audit-113-log-data-sufficiency-and-dogfood-system-audit.md
    date_raised: 2026-09-22
    severity: high
    status: fixed
    fix_applied_date: '2026-09-22'
    verified_in_audit: agent/reports/audit-113-log-data-sufficiency-and-dogfood-system-audit.md
    summary: "Enriched telemetry and logging infrastructure across SessionState, Filter, save_crash, and DogfoodOptimizer to record granular SkipReason distributions, machine-readable crash_context.json metadata, task lifecycle/yield metrics, and automated filters.yml starvation tuning."
    affected_files:
      - InstaAddict/core/session_state.py
      - InstaAddict/core/filter.py
      - InstaAddict/core/utils.py
      - InstaAddict/core/bot_flow.py
      - InstaAddict/core/dogfood.py
      - test/test_tuning_and_operational_fixes.py

  - id: CO-067
    audit_report: agent/reports/audit-115-dogfood-optimizer-tuning-and-crash-analysis.md
    date_raised: 2026-09-23
    severity: high
    status: fixed
    fix_applied_date: '2026-09-23'
    verified_in_audit: agent/reports/audit-117-post-impl-crash-remediation-and-dogfood-modernization.md
    summary: "Harden HomeView.navigateToSearch and SearchView.navigate_to_target against transient JsonRpcError/UiObjectNotFoundException on action bar search button clicks and input focus."
    affected_files:
      - InstaAddict/core/views.py
      - test/test_tuning_and_operational_fixes.py

  - id: CO-068
    audit_report: agent/reports/audit-115-dogfood-optimizer-tuning-and-crash-analysis.md
    date_raised: 2026-09-23
    severity: high
    status: fixed
    fix_applied_date: '2026-09-23'
    verified_in_audit: agent/reports/audit-117-post-impl-crash-remediation-and-dogfood-modernization.md
    summary: "Remove EmptyList from decorators.py restart tuple so that empty/restricted user lists do not trigger false-positive crash restarts, crash dumps, and Instagram relaunch."
    affected_files:
      - InstaAddict/core/decorators.py
      - test/test_tuning_and_operational_fixes.py

  - id: CO-069
    audit_report: agent/reports/audit-115-dogfood-optimizer-tuning-and-crash-analysis.md
    date_raised: 2026-09-23
    severity: medium
    status: fixed
    fix_applied_date: '2026-09-23'
    verified_in_audit: agent/reports/audit-117-post-impl-crash-remediation-and-dogfood-modernization.md
    summary: "Modernize DogfoodOptimizer with sliding session window (last 5 sessions) and structured traceback parsing to eradicate historical baggage and delay-mean placebo recommendations."
    affected_files:
      - InstaAddict/core/dogfood.py
      - test/test_tuning_and_operational_fixes.py
