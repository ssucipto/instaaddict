---
id: route-042
title: Comprehensive Audit & Review Remediation of Implementation Gaps and Shortcuts
task_type: plugin-fix
milestone: milestone-8-auto-upload-pipeline
complexity: medium
executor: Antigravity
context_required:
  - agent/reports/audit-043-implementation-gaps-inconsistencies-shortcuts.md
  - agent/reports/review-034-code-quality-and-improvements.md
files_affected:
  - InstaAddict/plugins/interact_reels.py
  - InstaAddict/plugins/upload_posts.py
  - InstaAddict/core/views.py
  - InstaAddict/core/interaction.py
  - InstaAddict/core/gemini_vision.py
  - InstaAddict/core/report.py
  - config-examples/config.yml
  - test/test_upload_posts.py
tokens_est: 8000
tokens_actual:
cost_est_usd:
cost_actual_usd:
created: 2026-09-14
completed: 2026-09-14
override_reason:
---

## Description
Address all 9 findings identified during Audit #043 and Review #034 to eliminate shortcuts, gaps, and latent runtime defects:
1. Register `--reels-topic` in `InteractReelsPlugin.arguments` and guard `configs.args.reels_topic` attribute access.
2. Register `--upload-queue-dir` in `UploadPostsPlugin.arguments`, integrate with queue directory discovery, and document in config.
3. Initialize module-level globals (`args`, `configs`, `ResourceID`) in `views.py` and `interaction.py` and defensively guard `LanguageView.setLanguage`.
4. Migrate file publishing moves in `upload_posts.py` to `shutil.move()` to support cross-filesystem directory mounts.
5. Remediate bare `except:`, out-of-bounds `sys.argv` parsing, and duplicate imports in `gemini_vision.py`.
6. Fix corrupted Unicode log strings in `interact_reels.py`.
7. Expand composer modal dismissal regex in `upload_posts.py` (`(?i)^(OK|Continue|Not now|Got it|Dismiss)$`).
8. Harden OCR error handling in `views.py` against `UnboundLocalError`.
9. Include upload metrics parity in `report.py` `print_full_report`.

## Acceptance Criteria
- [ ] All 9 findings from Audit #043 and Review #034 resolved.
- [ ] Python syntax and static validation cleanly passes.
- [ ] 100% pass rate maintained across all 68 unit tests.
- [ ] Live emulator verification confirms clean plugin execution.
- [ ] Carryover CO-013 marked status: fixed.
