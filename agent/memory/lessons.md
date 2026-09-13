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
