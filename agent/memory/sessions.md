# Session Memory
# Format: YAML blocks, last 3 loaded per session, auto-compacted at 15 entries
# DO NOT edit manually — updated by /acp-commit

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