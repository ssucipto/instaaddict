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

- date: 2026-09-24
  name: zero-displacement-grid-trap-breaker-and-detail-verification
  description: "Verify detail view transitions via OpenedPostView.is_post_opened() with coordinate-calculated center taps and 2-attempt retries, paired with consecutive unidentifiable author circuit breakers to defeat zero-net displacement oscillations in list and grid traversals."
  context: "Android mobile automation when clicking thumbnail cells in a RecyclerView (such as hashtag/location grids) may trigger long-press peek previews or fail to navigate, leaving the UI trapped on the grid where upward corrective swipes (3x UP) and downward pagination swipes (1x NEXT) create an infinite 0-displacement loop."
  solution: "In nav_to_hashtag_or_place(), compute element center bounds to execute crisp coordinate taps, dismiss lingering peek modals, and verify is_post_opened() across both feed and Reels/Clips root containers before entering handling loops. In handle_posts(), implement an instant grid-exit breakout check and a 5-consecutive unidentifiable author circuit breaker that marks the source dead in HashtagManager, triggers soft recovery via check_micro_stall(), and conditions watchdog heartbeats strictly on verified progress."

- date: 2026-09-25
  name: fast-adb-metadata-fallback-and-transport-health-telemetry
  description: "Bypass hung or lagging accessibility RPC daemons by falling back to parameterized direct ADB shell commands (<50ms) for core device metadata, and feed transport metrics into self-learning dogfood optimizers."
  context: "Android mobile automation where UiAutomator/atx-agent daemons crash or disconnect (e.g. Android 17 emulator Skia rendering ANR loops or HTTP timeouts), multiplying exponential retries into fatal 45-minute hangs before bot start."
  solution: "In DeviceFacade.get_info() and get_device_info(), reduce RPC attempts and query ro.product.model, ro.build.version.sdk, wm size, wm density, and dumpsys power via direct adb shell. Cache results in a single query pass. Track RPC disconnects, ADB timeouts, and device health latency in PerformanceTracker and expose them to DogfoodOptimizer for autonomous health recommendations."
- date: 2026-09-25
  name: multi-process-fleet-supervision-and-atomic-beacon-ipc
  description: "Supervise N independent mobile automation bot processes across separate Android emulators with atomic status beaconing, targeted ADB reconnects, bounded log rotation, and zero-downtime hot-reloads."
  context: "Multi-account mobile app automation where running multiple accounts in threads or via sequential in-app account switching causes global singleton collisions, memory leaks, crash cascades, and shared quota starvation."
  solution: "Isolate each account into a distinct OS subprocess targeting an emulator via --device; write telemetry atomically to .status.json using tmpfile rename; handle Windows file-lock sharing violations via retry loops; assert sys.boot_completed and init.svc.bootanim before start; bound stdout logs to 10MB; suppress global adb kill-server in favor of adb -s <id> reconnect; and implement zero-downtime configuration reload with diff-based process recycling."
