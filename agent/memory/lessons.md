# Correction Log — Filtered by task_type before loading
# Populated automatically when developer says "log it" or "wrong, log this"
# Max 5 entries loaded per session, filtered to current task_type + priority:high

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


