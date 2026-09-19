# Reusable Code Patterns
# Populated automatically by /acp-commit when patterns are identified
# Format: date-stamped YAML entries, max 60 days active

- date: 2026-09-15
  name: vlm-retry-backoff-and-job-prioritization
  description: "Wrap multimodal VLM requests in a 5-attempt retry loop with exponential delay on 500/503/504 errors and prioritize upload jobs at the head of execution queues to eliminate starvation from downstream interaction crashes."
  context: "Vision AI inference on Google Gemini models and scheduled content publishing in bot automation systems."
  solution: "In gemini_vision.py, catch transient Google API timeouts and retry with progressive sleep. In bot_flow.py, dynamically relocate upload-posts to jobs_list[0] before randomizing subsequent interaction tasks."

- date: 2026-09-16
  name: modal-dialog-dismissal-and-stuck-recovery
  description: "Multi-tier non-destructive popup dismissal prioritizing negative choices (No thanks, Remind me later, Not now, Cancel) and 4-tier escalated stuck-screen recovery with clean application restart."
  context: "Android UI automation when in-app or system popups (e.g., Rate Instagram, notifications, ANR) overlay screens and deadlock accessibility tab navigation."
  solution: "Implement UniversalActions.dismiss_dialog with regex and resource ID sweeps; integrate dialog checks into TabBarView._navigateTo and post-upload steps; provide UniversalActions.recover_stuck_screen with back presses and app_stop/app_start fallback."

- date: 2026-09-16
  name: parameterized-subprocess-and-credential-isolation
  description: "Eliminate command injection by substituting formatted shell=True strings with parameterized argument lists and defensive timeouts, while isolating all persona and token credentials strictly into uncommitted local directories."
  context: "ADB automation, OS interaction, and LLM multimodal bot configurations requiring public git safety and OWASP A03 injection defense."
  solution: "Enforce shell=False with explicit timeout across subprocess.run/Popen; decouple core module fallbacks to generic creator roles; load private personas and tokens dynamically from local accounts/<user>/ and .env."

- date: 2026-09-17
  name: cross-platform-rich-tui-with-safe-glyph-fallbacks
  description: "Live terminal user interface with thread-safe state synchronization, safe console glyph fallbacks for legacy Windows codepages, and atexit cursor restoration."
  context: "Long-running CLI automation tools requiring live statistics, progress tracking against safety limits, and rolling log streams without clobbering stdout across UTF-8 and non-UTF-8 consoles."
  solution: "Implement safe_glyph() checking sys.stdout.encoding with ASCII fallbacks; use rich.live.Live with safe_box=True; register atexit.register(self.stop) for clean cursor restoration; swap logging handlers to route log records to a bounded deque ring buffer during execution."

- date: 2026-09-18
  name: peek-preview-action-ingestion-and-circuit-breaker
  description: "Detect floating Peek Preview (long-press/3D Touch) modals, ingest actions directly from the preview context menu to avoid wasted navigation effort, dismiss immediately, and enforce consecutive failure circuit breakers with verified exit loops."
  context: "Mobile app automation (Instagram, etc.) where touch sensitivity or RPC latency triggers long-press context modals instead of opening views, resulting in trapped navigation and zero-action timeout cascades."
  solution: "Check for preview context buttons ('Like', 'Comment') on post open; execute like directly on the preview menu and register telemetry if present; calculate explicit element center coordinates for instantaneous tap events; enforce a 2-consecutive failure circuit breaker on un-openable profiles; and verify exit with a multi-iteration loop checking _is_still_on_profile() before proceeding."

- date: 2026-09-19
  name: follower-count-delta-guard-and-profile-header-badge
  description: "Bypass follower list traversal when account follower count is unchanged via delta guard on atomic local cache, and eliminate following-list inspection by reading native profile header 'Follows you' badge."
  context: "Social platform automation (Instagram) where verifying follow-back status previously required scraping thousands of followers and navigating deep into candidate following lists."
  solution: "Compare session_state.my_followers_count with storage cached count; if delta is 0, skip follower scraping entirely. Cache harvested followers in a persistent JSON set for O(1) membership check. When candidate profile is opened, inspect the profile header for 'Follows you' badge across 4 resilient fallback tiers, completely eliminating candidate following-list navigation."

