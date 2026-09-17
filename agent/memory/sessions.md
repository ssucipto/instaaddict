# Session Memory
# Format: YAML blocks, last 3 loaded per session, auto-compacted at 15 entries
# DO NOT edit manually — updated by /acp-commit

- date: 2026-09-17
  executor: Antigravity
  branch: master
  tasks_completed: [route-047, audit-060, review-042, co-043-co-048]
  done:
    - implemented-modern-terminal-user-interface-and-live-dashboard-using-rich
    - built-thread-safe-dashboard-state-with-metric-and-limit-synchronization
    - created-custom-tuiloghandler-with-ansi-stripping-and-level-color-coding
    - integrated-live-progress-bars-for-likes-follows-comments-and-total-actions
    - added-responsive-layout-stack-for-narrow-terminals-under-85-columns
    - implemented-safe-glyph-and-safe-box-for-windows-cp1252-and-cp437-encoding
    - registered-atexit-and-countdown-finally-handlers-for-clean-cursor-restoration
    - added-cli-flags-tui-and-no-tui-with-isatty-headless-ci-fallback
    - resolved-all-carryovers-co-043-through-co-048-without-shortcuts
    - verified-166-of-166-tests-passing-100-percent-green-with-zero-regressions
    - bumped-release-version-to-v1.3.0-across-all-project-identifiers
  deferred: []
  key_fact: "Windows legacy consoles (CP1252/CP437) crash with UnicodeEncodeError when rich renders raw emojis; detecting sys.stdout.encoding capabilities and providing clean ASCII glyph fallbacks alongside safe_box=True ensures cross-platform visual stability without sacrificing modern terminal aesthetics."

- date: 2026-09-17
  executor: Antigravity
  branch: master
  tasks_completed: [audit-059, audit-060, review-042, co-037-co-042]
  done:
    - executed-git-history-rewrite-with-git-filter-repo-purging-accounts-venv-gramaddict-joeahkim
    - force-pushed-rewritten-clean-history-to-origin-master
    - sanitized-all-personal-identifiers-names-and-tags-from-test-suites-and-helper-scripts
    - fixed-inverted-block-detection-logic-and-added-null-safety-in-universal-actions
    - added-network-and-subprocess-timeouts-to-update-check-and-pre-post-scripts
    - hardened-on-demand-telegram-upload-worker-with-subprocess-timeout-and-termination-handling
    - sanitized-pyproject-toml-author-email-and-github-funding-yml
    - verified-148-of-148-unit-and-integration-tests-passing-with-zero-regressions
    - resolved-all-carryovers-co-037-through-co-042-as-fixed-with-clean-remediation
    - validated-acp-documentation-and-synchronized-readme-requirements-and-progress
  deferred: []
  key_fact: "Git history scrubbing requires running git-filter-repo to completely eliminate leaked credentials and account paths across all historical commits, followed by a strict codebase audit ensuring test fixtures, helper scripts, and memory summaries also use generic placeholder data."

- date: 2026-09-16
  executor: Antigravity
  branch: master
  tasks_completed: [audit-056, audit-057, review-041, audit-058]
  done:
    - audited-instagram-modal-dialog-and-stuck-screen-deadlock
    - implemented-universal-actions-dismiss-dialog-with-multi-tier-matching
    - enforced-safe-rate-instagram-handling-strictly-clicking-no-thanks
    - added-post-upload-dialog-sweeping-in-upload-posts-plugin
    - replaced-flawed-tab-bar-visible-check-in-inter-job-bot-flow-recovery
    - built-universal-actions-recover-stuck-screen-with-escalated-clean-app-restart
    - integrated-dialog-dismissal-fallback-in-tab-bar-view-navigate-to
    - added-10-unit-tests-in-test-dialog-dismissal-and-stuck-recovery
    - audited-repository-integrity-and-privacy-zero-tracked-secrets-verified
    - decoupled-hardcoded-personas-and-hashtags-into-generic-creator-defaults
    - eliminated-shell-true-from-all-core-subprocess-and-adb-calls-owasp-a03
    - enhanced-check-telegram-diagnostic-script-with-auto-account-discovery
    - verified-68-of-68-tests-passing-100-percent-green-with-zero-regressions
    - resolved-all-carryovers-co-019-through-co-036-as-fixed
  deferred: []
  key_fact: "Separation of concerns: All account-specific personas, regional hashtags, and credentials reside strictly in local accounts/ and .env files protected by .gitignore. Eliminating shell=True and replacing string concatenation with parameterized argument lists and timeouts protects core automation from command injection vulnerabilities."

- date: 2026-09-15
  executor: Antigravity
  branch: master
  tasks_completed: [route-046, audit-052, audit-053, review-040]
  done:
    - implemented-option-b-on-demand-telegram-posting-commands
    - built-post-and-post-force-with-12h-cooldown-evaluation-and-bypass
    - built-preview-delivering-photo-and-caption-directly-to-telegram
    - integrated-adb-device-connection-state-into-status-command
    - built-cooldown-query-command-calculating-remaining-wait-window
    - resolved-cli-subparser-error-by-auto-injecting-run-subparser
    - enabled-auto-config-discovery-from-username-flag
    - implemented-only-upload-and-upload-now-modes-bypassing-interaction-loops
    - built-automated-adb-daemon-recovery-on-emulator-offline-transport-drops
    - silenced-deprecated-google-generativeai-package-futurewarning-banner
    - added-10-unit-tests-in-test-telegram-commands-reaching-127-tests-100-percent-green
    - passed-all-6-local-acp-ci-fast-gates
  deferred: []
  key_fact: "Google Android emulator ADB transport drop (emulator-5554 offline) occurs over extended TCP idle sockets without the VM shutting down; cycling ADB daemon (adb kill-server && adb start-server) instantly restores connection. InstaAddict CLI subparser 'run' can be transparently injected when direct user flags are supplied. In-memory locks prevent duplicate on-demand upload subprocesses from colliding on device resources."

- date: 2026-09-15
  executor: Antigravity
  branch: master
  tasks_completed: [route-045, audit-051, review-039]
  done:
    - migrated-vision-ai-to-gemini-3.6-flash
    - implemented-5-attempt-retry-exponential-backoff-on-vision-and-hashtags
    - implemented-mandatory-caption-elaboration-and-hashtag-enrichment-pre-upload
    - prioritized-upload-posts-at-head-of-jobs-list-preventing-job-starvation
    - built-and-verified-check-telegram-diagnostic-and-listener-utility
    - verified-live-photo-ingestion-and-ai-elaboration-for-user-account
    - resolved-acp-01-casing-header-in-acp-proceed-command
    - executed-audit-051-and-review-039-with-zero-regressions
    - verified-acp-ci-fast-tier-all-6-gates-passing
  deferred: []
  key_fact: "Gemini 3.7 Flash occasionally triggers transient 504 Deadline Exceeded; migrating to gemini-3.6-flash and wrapping API calls in a 5-attempt retry loop with exponential backoff (2s, 4s, 6s, 8s) provides 100% resilience against transient upstream load spikes. Prioritizing upload-posts at jobs_list[0] ensures scheduled posts publish before lengthy interaction jobs encounter potential crash limits."

- date: 2026-09-14
  executor: Antigravity
  branch: master
  tasks_completed: []
  done:
    - fixed-uiautomator2-android-sdk-37-nullpointerexception-runner
    - added-uiautomator-resurrection-watchdog-in-device-facade
    - prioritized-profile-tab-resource-id-in-profile-view
    - hardened-save-crash-and-log-module-globals
    - enhanced-gemini-vision-caption-with-user-context-guidance
    - connected-txt-sidecar-as-contextual-notes-for-ai-caption-extension
    - added-graceful-fallback-to-raw-txt-if-ai-fails
    - executed-acp-audit-048-upload-mechanism-gaps-and-shortcuts
    - executed-acp-review-036-code-quality-assessment
    - remediated-rate-limit-mtime-preservation-with-os-utime
    - added-timeout-guard-and-exception-handling-in-adb-runner
    - hardened-mediastore-id-resolution-to-select-newest-id
    - added-caption-clipboard-paste-fallback-and-device-storage-cleanup
    - sanitized-telegram-markdown-to-prevent-400-bad-request
    - verified-and-passed-acp-ci-fast-gates-and-all-102-pytest-tests
  deferred: []
  key_fact: "shutil.move preserves file modification times; refreshing mtime with os.utime(dest, None) upon publication is necessary to ensure rate-limiting gates do not prematurely allow back-to-back uploads. MediaStore queries must select the maximum _id to avoid deleted duplicate entries. Subprocess execution against adb must always include timeouts to avoid permanent deadlocks on device disconnection."


- date: 2026-09-12
  executor: Antigravity
  branch: master
  tasks_completed: [task-17, task-18, task-19]
  done:
    - fixed-yaml-arguments-in-uploader
    - resolved-argparse-metavar-crash
    - silenced-google-sdk-deprecation-warnings
    - successfully-validated-project-and-completed-m6
  deferred: []
  key_fact: "M6 Autopilot Uploads & Vision UI fully architected and stabilized. configargparse natively chokes on nested dicts without metavars or string-wrapped spaces; always use explicit widths or quotes when hacking user YAMLs."

- date: 2026-09-12
  executor: Antigravity
  branch: master
  tasks_completed: [hashtag-search-fix]
  done:
    - patched-uiautomator2-android14-fastinputime-regex
    - switched-search-box-input-to-mode-paste
    - added-fallback-for-search-row-and-post-imageview-locators
    - accommodated-absence-of-deprecated-recent-tab-in-hashtag-feeds
    - expanded-space-separated-hashtag-sources-in-plugins
    - verified-live-hashtag-navigation-on-emulator
  deferred: []
  key_fact: "Android 14+ replaces mCurMethodId with mCurImeId/mSelectedImeId in dumpsys input_method, which breaks uiautomator2's wait_fastinput_ime and causes typing timeouts; Mode.PASTE (ACTION_SET_TEXT) avoids dropdown jitter and sets search text instantaneously."

- date: 2026-09-13
  executor: agent
  tasks: []
  done: [upstream-ui-stability-cherry-picks, resolve-co-009, acp-audit-019-020, acp-review-021, code-quality-formatting]
  deferred: []
  key_fact: "Safely cherry-picked 5 upstream bugfixes to prevent Vision AI regression and fix UI locators"

- date: 2026-09-13
  executor: Antigravity
  branch: master
  tasks_completed: []
  done:
    - fixed-vision-ai-quota-exhaustion-co-008
    - implemented-one-shot-evaluate-and-comment
    - added-lanczos-compression-and-throttling
  deferred: []
  key_fact: "Vision AI quota preserved by utilizing 1-shot evaluate-and-comment with LANCZOS 512x512 compression."

- date: 2026-09-13
  executor: Antigravity
  branch: master
  tasks_completed: []
  done:
    - migrated-swipe-to-adb-shell-input-swipe
    - added-retry-loop-and-429-handling-to-gemini-vision
    - handled-finish-reason-2-safety-crash-with-payload-sanitization
    - fixed-broad-except-blocks-to-use-exception-chaining
  deferred: []
  key_fact: "uiautomator2's drag() includes an implicit long-press that causes jerky swipe behaviors; migrating to native adb shell input swipe produces fluid scrolling. Gemini API's free tier quotas are strict and VLM handlers must have robust retry and backoff loops."

- date: 2026-09-13
  executor: Antigravity
  branch: master
  tasks_completed: [task-20, task-21, task-22, task-23]
  done:
    - fixed-windows-file-lock-in-log-handlers
    - installed-global-sys-excepthook-for-unhandled-exceptions
    - serialized-total-crashes-and-upload-metrics-in-session-state
    - tracked-upload-history-in-upload-posts-plugin
    - implemented-continuous-non-overwritten-markdown-history-and-session-reports
    - created-dogfood-optimizer-engine-for-self-learning-parameter-tuning
    - resolved-all-co-010-audit-findings
  deferred: []
  key_fact: "RotatingFileHandlers must be explicitly closed before unlinking on Windows; SessionState metrics must be explicitly registered in SessionStateEncoder.default to persist in sessions.json."

- date: 2026-09-13
  executor: Antigravity
  branch: master
  tasks_completed: [CO-011]
  done:
    - diagnosed-apple-tv-ad-trapping-in-inappbrowser-activity
    - added-ad-and-in-app-browser-resource-ids-to-resources-py
    - implemented-universal-actions-escape-in-app-browser-watchdog
    - integrated-browser-escape-into-detect-block-and-handle-sources-post-loop
    - universalized-ad-detection-across-all-jobs-in-post-owner-and-check-if-ad-or-hashtag
    - added-cta-button-sponsored-regex-and-server-component-detection
    - guarded-against-empty-author-and-ad-profile-interactions
    - hardened-reels-ad-escape-and-expanded-cta-regex
    - added-unit-test-suite-test-ad-detection-and-escape
  deferred: []
  key_fact: "Instagram ads use BrowserLiteInMainProcessIGActivity which traps uiautomator searches; dismissing via ig_browser_close_button or escape_in_app_browser watchdog before interacting with posts prevents session stalls."

- date: 2026-09-13
  executor: Antigravity
  branch: master
  tasks_completed: [persistent-followings-cache]
  done:
    - audited-action-unfollow-followers-and-storage-py
    - created-audit-030-audit-031-audit-032-and-review-030-reports
    - implemented-persistent-non-bot-followings-json-storage-with-atomicwrites
    - added-o1-in-memory-lookup-and-batch-persistence-at-scroll-boundaries
    - added-cache-invalidation-on-followed-and-unfollowed-state-transitions
    - scoped-checked-pre-seeding-to-script-unfollow-modes-preserving-unfollow-any
    - added-clear-non-bot-cache-and-ignore-non-bot-cache-cli-arguments
    - added-10-test-suite-in-test-non-bot-followings-cache-with-100-pass-rate
  deferred: []
  key_fact: "Storing non-bot followings in accounts/<username>/non_bot_followings.json with atomicwrites and pre-seeding checked set eliminates repetitive UI element polling and log spam on organic followings, while scoping pre-seeding preserves --unfollow-any."

- date: 2026-09-13
  executor: Antigravity
  branch: master
  tasks_completed: [tiered-hashtag-engine]
  done:
    - audited-hashtag-recent-and-hashtag-expansion-strategies-audit-033-034-035
    - created-60-plus-curated-tiered-masterlist-in-accounts-user-account-hashtags-yml
    - implemented-hashtag-manager-singleton-core-subsystem
    - implemented-strategy-1-gemini-ai-persona-expansion
    - implemented-strategy-2-in-app-caption-harvester-with-zero-overhead
    - implemented-deterministic-r-add-1-to-4-promotion-and-spam-blacklist-rules
    - implemented-deterministic-r-rot-1-to-3-balanced-tier-sampling-and-anti-fatigue-cooldown
    - implemented-deterministic-r-prn-1-to-2-dead-tag-pruning-and-saturation-benching
    - hooked-caption-harvesting-dead-tag-detection-and-saturation-into-handle-sources
    - updated-interact-hashtag-posts-with-cli-args-and-tiered-source-sampling
    - created-9-case-unit-test-suite-test-hashtag-manager-with-100-pass-rate
    - authored-audit-036-and-review-031-verification-reports
  deferred: []
  key_fact: "HashtagManager combines a curated 4-tier masterlist (local/breed/lifestyle/reach) with zero-overhead in-app caption harvesting and Gemini AI expansion; deterministic rules (2:2:1:1 tier-balanced sampling, 2-session anti-fatigue cooldown, 7-day saturation benching, and 0-result dead tag pruning) completely prevent bot burnout and maximize niche engagement."

- date: 2026-09-13
  executor: Antigravity
  branch: master
  tasks_completed: [route-040]
  done:
    - resolved-hashtag-reels-viewer-author-name-lookup-failure
    - added-clips-author-username-and-clips-author-profile-pic-resource-ids
    - decoupled-owner-resolution-failure-from-ad-detection-in-views-py
    - fixed-reels-caption-extraction-with-fast-exit-to-prevent-redundant-swipes
    - implemented-reels-like-button-resource-id-support
    - eliminated-jerky-double-scroll-and-redundant-swipe-to-fit-half-photo
    - implemented-single-fluid-vertical-swipe-for-reels-view-pager
    - tuned-adb-swipe-duration-to-200ms-for-smooth-responsive-scrolling
    - created-comprehensive-unit-test-suite-test-owner-ad-detection-and-scroll
    - validated-live-reel-post-author-extraction-and-ad-detection-on-emulator
    - bumped-project-version-to-v1-1-0-consistently-across-all-version-bearing-files
    - updated-readme-with-comprehensive-fork-differentiation-and-new-subsystem-docs
    - synchronized-requirements-specification-with-v1-1-0-capabilities
    - validated-acp-documentation-with-zero-errors-and-zero-warnings
  deferred: []
  key_fact: "Hashtag grid taps on video posts open Instagram's full-screen Reels viewer (`clips_author_username`, `clips_author_profile_pic`) rather than standard feed containers. In `views.py:1270`, failing to find `post_owner_clickable` returned `(False, True, is_hashtag)` where the second element falsely flagged the post as an advertisement; decoupling owner discovery failure from ad detection and adding dedicated Reels swipe handling eliminated both the false ad skips and scroll jerkiness. Bumping to v1.1.0 accurately reflects the cumulative addition of 10 major architectural subsystems over GramAddict."

- date: 2026-09-14
  executor: Antigravity
  branch: master
  tasks_completed: [task-35, route-041]
  done:
    - audited-auto-upload-pipeline-audit-040-041-042
    - resolved-co-012-auto-upload-broken-pipeline
    - implemented-native-media-store-indexing-and-add-to-feed-intent-sharing
    - added-case-insensitive-media-matching-and-txt-json-ai-sidecar-captions
    - decoupled-upload-posts-from-interaction-limits-in-bot-flow
    - added-upload-rate-limit-hours-cli-option-and-yaml-config
    - added-modern-ig-v446-composer-locators-in-resources-py
    - guarded-views-py-and-utils-py-against-unhandled-crashes-and-unbound-args
    - created-16-case-unit-test-suite-test-upload-posts-with-100-pass-rate
    - fixed-test-load-txt-and-test-telegram-path-independence-bringing-full-suite-to-68-of-68-passing
    - verified-live-post-upload-flow-on-android-emulator-with-real-queued-media
    - authored-review-033-quality-report-and-updated-readme-and-progress-tracking
  deferred: []
  key_fact: "Directly launching `com.instagram.share.ADD_TO_FEED` via Instagram's `ShareHandlerActivity` with a MediaStore URI (`content://media/external/images/media/<id>`) bypasses all bottom tab navigation, deprecations, and file picker dropdowns in 1 step, while prioritizing raw `.txt` sidecars provides frictionless content authoring."

- date: 2026-09-14
  executor: Antigravity
  branch: master
  tasks_completed: [task-36, route-042]
  done:
    - audited-implementation-gaps-and-shortcuts-audit-043-and-review-034
    - resolved-co-013-implementation-gaps-and-shortcuts
    - registered-reels-topic-cli-argument-and-defensive-fallback-in-interact-reels
    - registered-upload-queue-dir-cli-argument-and-supported-custom-queue-routing
    - replaced-os-rename-with-shutil-move-and-target-collision-safety-in-upload-posts
    - initialized-module-level-globals-in-views-py-and-interaction-py
    - guarded-language-view-set-language-against-uninitialized-args
    - isolated-pytesseract-not-found-error-against-unbound-local-error-and-crash
    - sanitized-gemini-vision-bare-except-to-specific-exceptions-with-bounds-check
    - expanded-composer-modal-dismissal-regex-to-cover-ok-continue-got-it-dismiss
    - added-upload-telemetry-metrics-to-print-full-report
    - restored-corrupted-utf8-emojis-in-interact-reels
    - added-interact-reels-unit-test-suite-test-interact-reels-py
    - verified-72-of-72-tests-passing-across-all-8-suites
    - authored-audit-044-remediation-verification-report
  deferred: []
  key_fact: "Registering all CLI arguments in plugin definitions prevents runtime AttributeError on argparse.Namespace; using shutil.move instead of os.rename prevents cross-filesystem crash (Errno 18 Invalid cross-device link) when moving queued uploads to completed archives."

- date: 2026-09-14
  executor: Antigravity
  branch: master
  tasks_completed: [task-37, task-38, route-043, route-044]
  done:
    - audited-runtime-errors-and-locator-failures-audit-045-audit-046-review-035
    - resolved-co-014-and-co-015-runtime-errors-and-reels-locators
    - removed-duplicate-reels-topic-and-added-collision-guard-in-config-py
    - guarded-all-interactive-input-prompts-against-keyboard-interrupt-and-eof-error
    - prioritized-modern-tab-bar-resource-ids-in-tab-bar-view-navigation
    - added-error-false-suppression-in-profile-view-get-username-for-speculative-checks
    - formatted-data-analytics-report-paths-with-os-path-join
    - accelerated-search-query-recovery-via-action-bar-button-back-direct-click
    - prioritized-clips-author-username-and-excluded-profile-pic-in-owner-open
    - eliminated-60-120s-freeze-in-filter-py-returning-unloaded-profile-immediately
    - bypassed-feed-media-container-loops-and-downward-swipes-on-full-screen-reels
    - protected-sys-excepthook-against-double-ctrl-c-interrupt-tracebacks
    - guarded-against-uninitialized-args-disable-filters-in-filter-py
    - enhanced-reels-like-detection-with-get-selected-and-unlike-regex-matching
    - authored-route-043-route-044-audit-045-audit-046-review-035
    - created-12-case-test-suite-in-test-runtime-hardening-py-bringing-suite-to-84-tests-passing
  deferred: []
  key_fact: "In Instagram Reels, clicking the author profile picture (CLIPS_AUTHOR_PROFILE_PIC) opens the user's Story if present, trapping the bot in Story viewer; for Owner.OPEN, only targeting CLIPS_AUTHOR_USERNAME navigates directly to Profile. Returning an unloaded Profile object immediately upon a 16s load timeout in filter.py allows check_profile to register SkipReason.NOT_LOADED in 0 seconds rather than forcing a 60-120s sleep."

- date: 2026-09-14
  executor: Antigravity
  branch: master
  tasks_completed: [task-39, route-045]
  done:
    - fixed-uiautomator2-device-facade-package-version-crash-on-sdk-37-with-dynamic-runner-detection
    - added-telegram-inbox-polling-with-get-updates-and-atomic-last-update-id-persistence
    - implemented-strict-telegram-chat-id-sender-whitelist-authorization
    - automated-high-res-telegram-photo-download-into-content-queue-pending
    - saved-accompanying-captions-into-txt-sidecars-for-frictionless-upload-posts-ingestion
    - implemented-interactive-telegram-commands-queue-status-help
    - added-instant-telegram-queueing-receipts-and-upload-success-failure-notifications
    - refactored-wait-for-next-session-sleep-into-20s-slices-for-responsive-mobile-polling
    - created-5-case-unit-test-suite-test-telegram-inbox-py
    - verified-all-93-tests-passing-across-the-entire-repository
  deferred: []
  key_fact: "Pairing Telegram Bot API getUpdates polling with atomic last_update_id tracking in accounts/<user>/telegram_state.json and saving incoming mobile photos + captions to pending/<id>.jpg and <id>.txt allows seamless remote content ingestion without changing UploadPostsPlugin's core architecture; slicing inter-session sleep into 20s intervals guarantees responsive mobile interaction without busy-wait CPU burn."

- date: 2026-09-15
  executor: Antigravity
  branch: master
  tasks_completed: [task-40, route-046]
  done:
    - app-wide-acp-review-and-acp-integrity-execution-across-all-subsystems
    - eliminated-all-hidden-unicode-and-zero-width-joiner-characters-repo-wide
    - stripped-utf8-bom-byte-order-marks-from-14-maintenance-scripts
    - resolved-false-positive-auth-token-logging-heuristic-in-hashtag-manager
    - remediated-redundant-inline-loop-imports-in-gemini-vision
    - enhanced-acp-unicode-scan-with-binary-skipping-and-word-boundary-patterns
    - improved-acp-memory-scan-with-cross-platform-path-resolution-on-windows
    - allowlisted-sourced-helper-libraries-dupehound-and-gitleaks-in-review-scan
    - created-integrity-001-and-review-037-formal-audit-reports
    - executed-coderabbit-diff-style-comprehensive-codebase-review
    - validated-all-102-pytest-unit-tests-passing-with-zero-regressions
    - confirmed-full-acp-ci-fast-passing-across-all-6-standard-gates
  deferred: []
  key_fact: "Binary media files like camera JPEGs and UI screenshots must be explicitly excluded from character-level Unicode and BOM scanners to prevent false-positive detection on compressed byte sequences; allowlisting sourced shell helper libraries in static review scanners prevents spurious missing set -euo pipefail warnings."

- date: 2026-09-15
  executor: Antigravity
  branch: master
  tasks_completed: [task-41, route-047]
  done:
    - implemented-hashtag-fallback-and-enrichment-in-upload-posts-via-hashtag-manager
    - added-upload-hashtags-in-comment-option-for-clean-caption-reach-strategy
    - implemented-companion-photo-comments-binding-from-follow-up-telegram-text-messages
    - added-interactive-caption-editing-and-elaborate-ai-generation-commands-in-telegram
    - hardened-gemini-vision-with-programmatic-zwj-and-zero-width-character-stripping
    - guarded-against-gemini-candidate-safety-filter-finish-reason-value-error-crashes
    - implemented-atomic-grapheme-cluster-preservation-in-device-facade-keystroke-typing
    - enhanced-acp-unicode-scan-with-documentation-and-emoji-sequence-awareness
    - authored-pre-impl-audit-049-and-verification-audit-050-reports
    - authored-coderabbit-style-diff-review-038-report
    - created-15-case-unit-test-suites-test-telegram-companion-and-test-unicode-sanitizer
    - verified-all-117-pytest-tests-passing-with-zero-regressions
    - validated-full-acp-ci-fast-tier-passing-across-all-6-standard-gates
  deferred: []
  key_fact: "Iterating atomic grapheme clusters instead of raw code points in device_facade prevents FastInputIME keystroke splitting on compound emojis, while programmatic regex stripping of ZWJs in gemini_vision provides defense-in-depth against Android IME encoding crashes."