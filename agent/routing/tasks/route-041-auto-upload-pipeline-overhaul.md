---
id: route-041
title: Production Auto-Upload Pipeline Overhaul & Robust Job Scheduling
task_type: python-code-fix
milestone: M8
complexity: high
executor: antigravity
context_required:
  - agent/reports/audit-040-auto-upload-investigation.md
  - agent/memory/audit-carryovers.md
files_affected:
  - InstaAddict/plugins/upload_posts.py
  - InstaAddict/core/bot_flow.py
  - InstaAddict/core/config.py
  - InstaAddict/core/resources.py
  - test/test_upload_posts.py
tokens_est: 10000
tokens_actual:
cost_est_usd: 0.00
cost_actual_usd:
created: 2026-09-14
completed: 2026-09-14
override_reason:
---

## Task Description

Overhaul the autonomous post upload pipeline (`UploadPostsPlugin`) to resolve all 7 findings from Audit #040 and address carryover CO-012:
1. **Case-Insensitive File Discovery**: Fix `f.endswith(ALLOWED_EXTENSIONS)` to be case-insensitive (`f.lower().endswith(ALLOWED_EXTENSIONS)`) so `.JPG`, `.PNG`, etc. are discovered.
2. **Comprehensive Logging & Zero Silent Exits**: Add explicit, informative log output whenever the queue is empty, rate-limited, or directories are missing.
3. **Robust Username Resolution**: Fallback from `configs.args.username` -> `session_state.my_username` -> directory extraction, preventing `IndexError`.
4. **Configurable Rate Limiting**: Add `--upload-rate-limit-hours` CLI option (default: 12, allows 0 to disable) and support in `config.yml`.
5. **Decouple Job Scheduling**: In `bot_flow.py`, separate `upload-posts` from interaction-limited active jobs so hitting like/follow limits does not skip scheduled uploads.
6. **Native ADD_TO_FEED Intent Sharing**:
   - Register pushed files into Android MediaStore to obtain valid `content://media/external/images/media/<id>` URIs.
   - Launch Instagram's exported `ShareHandlerActivity` via `com.instagram.share.ADD_TO_FEED` (with fallback to `android.intent.action.SEND`).
   - Directly load the exact target media into Instagram's editor in 1 step, bypassing fragile tab clicks and gallery element hunting.
7. **IG v446+ Composer UI Navigation**:
   - Automate Screen 1 (Crop/Audio) -> Screen 2 (Filters/Edit) using verified resource IDs (`com.instagram.android:id/media_thumbnail_tray_button`, `text='Next'`).
   - Automatically detect and dismiss the "Sharing posts" modal dialog (`text='OK'`).
   - Type caption into `com.instagram.android:id/caption_input_text_view`.
   - Tap `com.instagram.android:id/share_footer_button` / `text='Share'` and verify return to feed.
8. **Sidecar Format Support**: Read captions from both `{base_name}.txt` (raw text) and `{base_name}.json` (`{"caption": "..."}`).
9. **Comprehensive Unit Test Suite**: Build `test/test_upload_posts.py` with 100% pass rate.

## Acceptance Criteria

- [x] `.JPG`, `.JPEG`, `.PNG`, `.MP4` files are correctly matched regardless of case.
- [x] Explicit warnings/info logs are emitted on empty queue or rate limit triggers.
- [x] Both `{base_name}.txt` and `{base_name}.json` caption sidecars are supported.
- [x] `--upload-rate-limit-hours` is configurable via CLI and `config.yml`.
- [x] `upload-posts` is not aborted in `bot_flow.py` when interaction limits are reached.
- [x] Media is pushed and registered via MediaStore content URI on device.
- [x] Upload uses `com.instagram.share.ADD_TO_FEED` intent to open the exact target image directly in IG composer.
- [x] "Sharing posts" modal dialog is automatically dismissed if present.
- [x] Caption is entered into `caption_input_text_view` and post is shared via `share_footer_button`.
- [x] Unit tests pass 100%.
