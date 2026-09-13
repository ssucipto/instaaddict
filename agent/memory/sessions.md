# Session Memory
# Format: YAML blocks, last 3 loaded per session, auto-compacted at 15 entries
# DO NOT edit manually — updated by /acp-commit


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
