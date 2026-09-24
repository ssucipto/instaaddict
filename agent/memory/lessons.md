# Correction Log — Filtered by task_type before loading
# Populated automatically when developer says "log it" or "wrong, log this"
# Max 5 entries loaded per session, filtered to current task_type + priority:high

- date: 2026-09-24
  task_type: audit
  mistake: Navigating to hashtags clicked thumbnails blindly without verifying OpenedPostView.is_post_opened(), and handle_posts() lacked a consecutive unidentifiable author circuit breaker while unconditionally emitting BotWatchdog heartbeats on empty passes. This blinded the watchdog and allowed 3x Direction.UP author-search swipes and 1x downward scroll swipes to cancel each other out, locking the screen onto the same 6 thumbnails in an infinite 4+ hour loop.
  correction: Assert is_post_opened() with center-point tap retry in nav_to_hashtag_or_place(), add a strict nr_consecutive_unidentifiable limit (5) in handle_posts() that breaks out to the next hashtag, only record watchdog heartbeats on verified author/post progress, and wire UniversalActions.check_micro_stall() into feed loops.
  priority: high

- date: 2026-09-23
  task_type: feature
  mistake: _describes_a_post initially returned inner.get_desc() directly, which could
    be an empty string "". Callers (including _get_media_container's sliver-skip loop)
    use truthiness checks like `if content_desc:`, so "" silently passed the guard
    and was treated as a valid description, breaking sliver detection.
  correction: Always normalize falsy returns to None — `return inner_desc if inner_desc else None`.
    Write explicit tests for the empty-inner-desc case.
  priority: high

- date: 2026-09-22
  task_type: audit
  mistake: Discarding granular SkipReason enums into a scalar counter blinded closed-loop autotuning engines from diagnosing parameter starvation (e.g. min_followers, potency_ratio, business accounts). Furthermore, saving crash dumps without machine-readable JSON context (active job, current target, foreground package, uptime) slowed post-mortem diagnosis.
  correction: Capture exact SkipReason enum distributions in SessionState, record machine-readable crash_context.json in save_crash(), instrument task lifecycle and yield metrics in job_metrics, and empower DogfoodOptimizer to diagnose starvation and autotune filters.yml.
  priority: high

- date: 2026-09-21
  task_type: bugfix
  mistake: Peek Preview detection included Comment and Share in context_opt, falsely matching standard Reels and Posts and causing repeated device.back() dismissals that exited Instagram to the launcher. Additionally, is_tab_bar_visible() and bot_flow.py recovery loop lacked AppHasCrashed handling, causing fatal unhandled exceptions when querying closed app states.
  correction: Strictly require (Repost|Report) in is_peek_preview_opened(), catch AppHasCrashed in is_tab_bar_visible() returning False, and wrap profile recovery in try-except AppHasCrashed with self-healing open_instagram() relaunch and crash metric tracking.
  priority: high

- date: 2026-09-20
  task_type: bugfix
  mistake: Checking for "401" substring in error messages falsely matched retry delay floating-point seconds like 7.924074016s in rate limit errors, permanently tripping the Vision AI circuit breaker. Additionally, inspect_current_view raised EmptyList crashing follower harvest and likers loops.
  correction: Check for 429/quota first, use word-boundary regex r"\b401\b" to prevent false-positive auth circuit breaker trips, and wrap all inspect_current_view call sites in try-except EmptyList.
  priority: high

- date: 2026-09-20
  task_type: bugfix
  mistake: On Instagram search/subscreens the bottom tab bar is hidden; legacy fallback jumped to HomeView.navigateToSearch() which called unchecked .click() on missing action bar search buttons, crashing with UiObjectNotFoundError. The subsequent @run_safely restart() triggered an atx-agent uiautomator2 server restart, and calling navigateToProfile() without exception guards while on the splash screen crashed the entire process.
  correction: Implement TabBarView._escape_subscreens() with dialog dismissals and back navigation before declaring tabs missing, guard HomeView.navigateToSearch() with exists() checks, and wrap post-restart navigateToProfile() in retry/try-except handlers to absorb transient RPC restarts.
  priority: high

- date: 2026-09-19
  task_type: bugfix
  mistake: Double-tap likes and creator follows in interact_reels.py were strictly nested inside if comment_text:, causing likes and follows to be discarded when Gemini Vision was safety-blocked, rate-limited, or empty. Furthermore, pytest collected ad-hoc scripts from scratch/ trying to connect to offline emulators.
  correction: Decouple Reels likes, follows, and comments so each engagement action executes independently based on its own rate and limits, provide fallback comments when Vision AI is dead or throttled, and explicitly scope testpaths = ["test"] in pyproject.toml.
  priority: high

- date: 2026-09-12
  task_type: bugfix
  mistake: Hashtag search typed character-by-character while wait_fastinput_ime timed out, repeatedly erasing input, and space-separated hashtags were treated as a single query.
  correction: Use Mode.PASTE for search bar input, monkeypatch uiautomator2 current_ime regex for Android 14+ FastInputIME, split space-separated sources in hashtag plugins, and handle modern IG v446+ feeds without the Recent tab.
  priority: high

- date: 2026-09-13
  task_type: bugfix
  mistake: Bot clicked on sponsored ad headers/buttons (e.g. Apple TV ad) because ad detection was scoped only to feed and relied solely on secondary labels, getting trapped inside BrowserLite in-app browser activities.
  correction: Enforce universal ad detection (CTA buttons, sponsored regex, server-rendered components) across all interaction jobs, fast-exit on empty/invalid authors, and install a universal escape watchdog (UniversalActions.escape_in_app_browser) in loops and detect_block.
  priority: high

- date: 2026-09-15
  task_type: bugfix
  mistake: Upload-posts job was starved when placed later in shuffled jobs list and crashed before execution, and Gemini Vision failed on single transient 504 errors without retries.
  correction: Prioritize upload-posts at the head of bot session jobs_list, set 5 retries with short interval backoff on vision AI and hashtag enrichment, and enforce mandatory pre-upload caption elaboration.
  priority: high

- date: 2026-09-15
  task_type: feature-integration
  mistake: Direct CLI flags (e.g. python -m InstaAddict --username <user>) failed with argparse subparser invalid choice, and extended TCP idle sockets caused emulator-5554 to report offline which appeared like emulator crashes.
  correction: Auto-inject 'run' subparser when flags are passed, auto-map --username to accounts/<user>/config.yml, and implement automatic adb kill-server/start-server recovery in DeviceFacade upon offline status or connection failure.
  priority: high

- date: 2026-09-16
  task_type: bug-investigation
  mistake: PHOTO/CAROUSEL branch in interact_with_user did not call device.back() after like_post(), while the VIDEO branch did. This left the post view open and navigateToPost re-resolved the same RecyclerView child(index=N) on every iteration, causing an infinite same-photo loop.
  correction: Always call device.back() after photo/carousel like in interact_with_user, matching the VIDEO branch pattern. Add a settle sleep after the back-guard so RecyclerView re-lays out before the next child(index=N) lookup. On navigateToPost retry, re-resolve both row_view and post_view, not just post_view.
  priority: high

- date: 2026-09-16
  task_type: bugfix
  mistake: Instagram post-upload modal popups (such as "Rate Instagram", notification prompts, or ANRs) deadlocked the bot because TabBarView checked is_tab_bar_visible() which evaluated True on background views, skipping back-keys and failing navigateToProfile(), causing all subsequent scheduled jobs to be skipped.
  correction: Implement multi-tier UniversalActions.dismiss_dialog() prioritizing negative/dismissive responses ("No, thanks", "Remind me later", "Not now", "Cancel"), integrate dialog sweeping directly into TabBarView._navigateTo and post-upload flows, and provide a 4-tier UniversalActions.recover_stuck_screen() escalating to clean app restart (app_stop + app_start) rather than abandoning scheduled jobs.
  priority: high

- date: 2026-09-19
  task_type: bugfix
  mistake: Importing matplotlib.pyplot at top-level in data_analytics.py defaulted to TkAgg GUI backend on Windows, causing Tcl_AsyncCreate to bind async handlers to the startup thread; during multithreaded bot execution or shutdown, Tcl_AsyncDelete panicked with 'async handler deleted by the wrong thread'.
  correction: Force headless non-GUI backend via os.environ.setdefault('MPLBACKEND', 'Agg') at entrypoints (run.py, __main__.py, __init__.py), enforce matplotlib.use('Agg', force=True) before importing pyplot, guard optional matplotlib dependencies, and explicitly close figures with plt.close(fig).
  priority: high

- date: 2026-09-19
  task_type: bugfix
  mistake: Follows, unfollows, and comments remained zero in modern IG v446+ because selectors required clickable=True on text elements where only the parent ViewGroup is clickable (causing getFollowButton to fail and Filter to skip all profiles with NOT_LOADED), _comment swiped down on Reels (paging to previous reel) and only looked for row_feed_button_comment, and action_unfollow_followers used rigid index traversal.
  correction: Decouple clickable=True from text node searches and support content-description fallbacks, guard downward swipes on MediaType.REEL in _comment and match modern Reels comment buttons (comment_button/clips_comment_button), implement multi-tier comment confirmation (description regex/cleared edittext), and use resilient username discovery in following list rows.
  priority: high

- date: 2026-09-19
  task_type: bugfix
  mistake: Reels captions were falsely identified as missing because clips_caption_component is a ViewGroup container that returns empty strings for get_text()/get_desc(), and terminal hotkey 'U' was unresponsive on Windows/Unix because msvcrt and raw terminals emit ASCII control codes (e.g. \x15 for Ctrl+U) rather than literal characters, while requests were only polled at high-level job boundaries.
  correction: Extract Reels captions via a 5-tier strategy (direct attributes, child TextView traversal with username filtering, alternative selectors, XML hierarchy parsing, and trailing '...more' stripping), decode both raw control bytes/chars (\x13, \x15, \x04) and character fallbacks in keyboard listeners, and poll is_upload_requested() responsively inside inter-session sleep slices and long-running engagement loops.
  priority: high

- date: 2026-09-19
  task_type: bugfix
  mistake: Reels classified 100% of organic posts as ads because ad_cta_regex contained 'Subscribe' (creator badge) and recycled off-screen views matched 'Learn more', while post-view comments failed because device.back() was invoked immediately after liking (before _comment was called).
  correction: Exclude 'Subscribe' from ad_cta_regex and enforce spatial bounds (top > h*0.4, width > w*0.25) before classifying Reels ads, match inline_follow_button in Reels follow selector, and defer device.back() until after commenting finishes so post remains open during comment actions.
  priority: high

- date: 2026-09-19
  task_type: bugfix
  mistake: Directly assigning an integer to SessionState.totalFollowed violates its dict[str, int] contract, causing limit checks (sum(totalFollowed.values())) and reporting to crash with AttributeError or TypeError; casting range strings ("30-40") with int() fails with ValueError; and gating _comment() behind already_liked is not None and not already_liked starves commenting on already-liked posts.
  correction: Preserve SessionState.totalFollowed as a dictionary updated via add_interaction(), use get_value() for range-safe percentage parsing, and decouple comment evaluation from whether the post was freshly liked or already liked.
  priority: high

- date: 2026-09-19
  task_type: bugfix
  mistake: In handle_sources.py, handle_posts lacked post-commenting logic, rendering feed commenting dead code and leaving opened hashtag posts uncommented. In addition, caller duplicating session_state.totalComments += 1 double-counted comments because _comment() already increments it, and top hashtag posts were saturated with already-followed accounts.
  correction: Integrate post-view commenting directly into handle_posts with MediaType detection, respect profile_filter.can_comment(current_job) and comment_percentage with get_value range parsing, let _comment() be the single source of truth for totalComments, record feed interactions via storage.add_interacted_user, and drive follower discovery via blogger-followers and interact-reels with end-if-likes-limit-reached set to false.
  priority: high
- date: 2026-09-20
  task_type: bugfix
  mistake: Bot sessions terminated prematurely at 44 minutes because external rate limit backoffs (60s sleep) and cached non-bot skips lacked watchdog heartbeats, triggering false-positive KEYCODE_BACK alarms that reached total-crashes-limit (5/5). Additionally, EmptyList was erroneously raised as an unhandled exception in iterate_over_followers, list_view.scroll crashed on IG v447 UI, Direction.BOTTOM was referenced despite Direction only containing UP/DOWN/LEFT/RIGHT, and stop_bot() failed to stamp finishTime or guard against None args/configs.
  correction: Wrap API rate-limit sleeps in _safe_rate_limit_sleep() with watchdog pause/resume and 5s chunked heartbeats, emit heartbeats during list iterations, catch and handle EmptyList gracefully in iterate_over_followers, fall back to device.swipe(Direction.UP) on list scroll failures, stamp session_state.finishTime on bot exit, and defensively guard args and configs against NoneType in utils.py.
  priority: high

- date: 2026-09-20
  task_type: bugfix
  mistake: SessionStateEncoder omitted finish_time during JSON serialization of SessionState, causing saved sessions in accounts/<user>/sessions.json to lack finish_time; when data_analytics.py ran on startup, raw dictionary indexing session["finish_time"] crashed with KeyError, and telegram.py caught only ValueError rather than (ValueError, KeyError, TypeError).
  correction: Serialize finish_time in SessionStateEncoder.default(), defensively use session.get("finish_time") and session.get("start_time") with multi-format parsing (%Y-%m-%d %H:%M:%S.%f and %Y-%m-%d %H:%M:%S) in data_analytics.py returning None, add null guards in duration and growth plots, and expand telegram.py duration calculation exception guards.
  priority: high

- date: 2026-09-20
  task_type: bugfix
  mistake: Task skip shortcuts (CTRL+S, 's', 'S', 'n', 'N') appeared non-functional to users because there was zero on-screen acknowledgment or audio feedback when pressed, while background tasks remained trapped in uninterruptible random_sleep delays (up to 15-25s) or dense inner loops without per-item skip checks.
  correction: Provide immediate visual acknowledgement via high-visibility header badges ("⚡ [SKIP PENDING]"), activity panel alerts ("🚨 [CTRL+S RECEIVED] Task Skip Pending"), flashing footer alerts ("⚡ SKIPPING TASK..."), terminal bell ("\a"), slice random_sleep into 0.1s interruptible steps gated by DashboardManager.is_active(), and place non-destructive is_skip_task_requested() checks inside item iteration loops.
  priority: high

- date: 2026-09-21
  task_type: bugfix
  mistake: In navigateToPost, checking if opened_post_view.is_post_opened() or not self._is_still_on_profile() ran before checking is_peek_preview_opened(). Because Peek Preview dims the profile tabs underneath, _is_still_on_profile() returned False, causing the bot to falsely conclude the post was opened normally and bypass Peek Preview interaction and dismissal. Furthermore, locator class restrictions (TextView|Button) failed on modern Jetpack Compose layouts where Repost/Report reside in contentDescription.
  correction: Always check opened_post_view.is_peek_preview_opened() FIRST in navigateToPost before checking profile exit. Use unrestricted class queries checking both textMatches and descriptionMatches for Repost/Report and Like/Unlike. Add UniversalActions.dismiss_peek_if_open() to UniversalActions.dismiss_dialog() sweep pass 0 and check_micro_stall(), and defensively clear peek overlays on open failures, profile exit, and unidentifiable post authors in feed loops.
  priority: high

- date: 2026-09-21
  task_type: bugfix
  mistake: When launching outside configured working-hours, the bot immediately enters scheduled sleep without updating the TUI dashboard activity or providing feedback in Telegram commands (/start, /status), leading users to perceive a startup regression where Instagram fails to open. Furthermore, target_app resolution in open_instagram and dismiss_peek_if_open accepted non-string objects (like MagicMock in tests), and SessionState.inside_working_hours failed when passed a raw string interval rather than a list.
  correction: Provide transparent Telegram feedback explaining working-hours sleep schedule on /start <arg> and /status, set dashboard_manager.state.status_message to 'SLEEPING' before entering wait_for_next_session, strictly enforce string type checking for target_app fallback ('com.instagram.android'), and auto-wrap string inputs to a list in SessionState.inside_working_hours.
  priority: high

- date: 2026-09-22
  task_type: bugfix
  mistake: BotWatchdog's 90s inactivity threshold fired Tier 1 recovery (2x KEYCODE_BACK) during lengthy emulator Instagram cold-starts and IME configuration (taking ~91s without heartbeats). The asynchronous back keys displaced Instagram from the Profile screen to the Home feed, causing ProfileView.getProfileInfo() to return None for all counters, which bot_flow.py immediately misclassified as an account soft-ban and aborted via sys.exit(2) after only 2m31s.
  correction: Instrument open_instagram() wait loops, IME config, AccountView.refresh_account(), and ProfileView.getProfileInfo() with record_heartbeat() checkpoints. Before aborting on None profile counters, execute a self-healing recovery in bot_flow.py that dismisses dialogs, re-navigates to Profile via TabBarView.navigateToProfile(), and retries getProfileInfo() before declaring a fatal soft-ban. Defensively guard configs.args and configs.device_id accesses against NoneType in utils.py.
  priority: high

- date: 2026-09-22
  task_type: bugfix
  mistake: Following scheduled sleep, emulator CPU spikes triggered an Android system ANR dialog ("Instagram isn't responding"). Watchdog inactivity fired KEYCODE_BACK during ANR resolution, displacing Instagram to the background. open_instagram() exited without confirming foreground status, and ProfileView(device) crashed unhandled with AppHasCrashed because ActionBarView.__init__ eagerly queried device.find() outside any try/except retry loop in start_bot().
  correction: Wrap ActionBarView._getActionBar() and __init__ in try/except AppHasCrashed setting self.action_bar = None; verify device._ig_is_opened() at conclusion of open_instagram(); emit watchdog heartbeats when tapping Wait on system ANR dialogs; guard choose_cloned_app against None configs/ResourceID; and wrap startup profile initialization in a 3-attempt retry loop in start_bot() with AppHasCrashed catching and open_instagram() relaunch.
  priority: high


