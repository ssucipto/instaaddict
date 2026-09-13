# Changelog

## v1.1.0 — Modern Reels Architecture, Dynamic Hashtag Engine & Fluid Swiping

Comprehensive release introducing modern Instagram (v446+) Reels viewer compatibility, tiered dynamic hashtag discovery, persistent non-bot followings caching, universal in-app browser escape watchdog, and fluid native swipe physics.

### Added
- **Modern Reels & Clips Viewer Compatibility**:
  - Full support for Instagram's full-screen video viewer (`clips_viewer_view_pager`, `root_clips_layout`, `clips_viewer_container`).
  - Added multi-tier author resolution for `clips_author_username`, `clips_author_profile_pic` (regex content description extraction), and `clips_author_info_component`.
  - Added native Reels like button support (`ResourceID.LIKE_BUTTON`).
  - Added fast Reel caption extraction (`CLIPS_CAPTION_COMPONENT`) with immediate termination to prevent futile scroll loops.
- **Tiered Masterlist & Dynamic Hashtag Discovery Engine (`HashtagManager`)**:
  - Curated 4-tier pool in `accounts/<username>/hashtags.yml` across Local Community, Breed/Niche, Lifestyle/Adventure, and Reach tiers.
  - Strategy 1: AI Gemini Persona Expansion (`--expand-hashtags`) synthesizing high-conversion niche tags grounded in account persona.
  - Strategy 2: Zero-overhead in-app caption harvesting (`harvest_from_caption`) tracking cross-session tag frequency in `discovered_hashtags.json`.
  - Enforced deterministic rules: R-ADD-1..4 (promotion thresholds, anti-spam blacklist, semantic relevance, tier assignment), R-ROT-1..3 (2:2:1:1 tier-balanced sampling, 2-session anti-fatigue cooldowns, shuffle), and R-PRN-1..2 (0-result dead tag pruning, 7-day saturation benching).
  - Added CLI options: `--expand-hashtags`, `--no-harvest-hashtags`, and `--hashtags-file`.
- **Persistent Non-Bot Followings Cache**:
  - High-performance atomic JSON storage in `accounts/<username>/non_bot_followings.json`.
  - Instant O(1) in-memory lookups and batch disk writes at scroll boundaries.
  - Pre-seeded checked set in `ActionUnfollowFollowers` for fast-skipping known non-bot accounts without UI polling or log spam.
  - Automatic cache invalidation on follow and unfollow state transitions.
  - Added CLI options: `--clear-non-bot-cache` and `--ignore-non-bot-cache`.
- **Universal Ad Detection & In-App Browser Escape Watchdog**:
  - Automated detection and dismissal of `BrowserLiteInMainProcessIGActivity` and external browser overlays via native close buttons, fallback back-presses, and foreground recovery.
  - Whitelisted Android system packages (`com.android.systemui`, `android`, IME keyboards) against false dismissal.
  - Bounded CTA button coordinate detection to prevent false ad classifications.
- **Task Sequence Randomizer**:
  - Implemented `--randomize-tasks` / `randomize_task_sequence` to shuffle job execution order on every session for human-like behavior.

### Changed & Improved
- **Decoupled Author Resolution from Ad Detection**:
  - Removed faulty `(False, True, is_hashtag)` return in `views.py` when author view is unclickable; returns `(False, False, is_hashtag)`. Organic posts with non-clickable headers are no longer falsely marked as advertisements and skipped.
- **Fluid Single-Swipe Navigation & 200ms Swipe Physics**:
  - Replaced jerky multi-swipe sequences with a single vertical swipe (80% down to 20% height) for Reels.
  - Removed redundant `HALF_PHOTO` swipe call in `handle_sources.py`.
  - Stripped obsolete 3-retry gap-view loop searching for deprecated `GAP_VIEW_AND_FOOTER_SPACE`.
  - Calibrated native ADB swipe duration to 200ms (`adb shell input swipe x1 y1 x2 y2 200`), achieving snappy and natural mobile flick gestures.

**Full diff**: `v1.0.3...v1.1.0`

## v1.0.3 — Production Telemetry, Error Hardening & Self-Learning System

Production-grade error handling, automated telemetry, continuous non-overwritten reporting, and closed-loop self-learning parameter optimization.

### Added
- **Error Trace Logging (`_error_trace.log`)**: Dedicated warning and error logger capturing third-party errors (`uiautomator2`, `adbutils`, network stack) alongside InstaAddict events.
- **Top-Level Crash Interception**: Installed global `sys.excepthook` to guarantee fatal unhandled Python exceptions are written to the error trace log before process exit.
- **Full State Telemetry**: Expanded `SessionState` and `SessionStateEncoder` to track and persist `totalCrashes`, `totalUploadsSuccess`, `totalUploadsFailed`, and `uploadHistory` into `accounts/{username}/sessions.json`.
- **Upload Outcome Recording**: Enhanced `UploadPostsPlugin` to log upload executions, file names, captions, and statuses directly into the active session state.
- **Continuous Markdown History**: Automated `save_markdown_history()` on session completion (`print_full_report()`), appending to `accounts/{username}/history.md` (never overwritten) and generating timestamped session summaries in `accounts/{username}/reports/session_{timestamp}.md`.
- **Dogfood Self-Learning Optimizer (`DogfoodOptimizer`)**: Implemented `InstaAddict/core/dogfood.py` to analyze run history, error patterns, and source yields, generating automated configuration tuning recommendations in `tuning_suggestions.json` and `tuning_suggestions.md`.
- **Enhanced Data Analytics Markdown Export**: Upgraded `InstaAddict/plugins/data_analytics.py` to render complete tables of interaction yields, crashes, and content queue uploads.

### Fixed
- **Windows File Lock Descriptor Leak**: Explicitly closed file handlers before calling `os.remove()` in `update_log_file_name()`, eliminating Windows `PermissionError: [WinError 32]`.
- **Swipe Jitter & Drag Stalls**: Replaced uiautomator2 dragging with native `adb shell input swipe` for smooth and natural scroll gestures.
- **Gemini API 429 Quota & Safety Hardening**: Added exponential backoff retry loops, 512x512 LANCZOS payload compression, and safety-block fallback sanitizers.

**Full diff**: `v1.0.2...v1.0.3`

## v1.0.2 — Instagram compatibility & reliability fixes

Two weeks of accumulated fixes for running InstaAddict against current Instagram versions (tested against 440.0.0.46.86), plus dependency and packaging cleanup.

### Instagram UI compatibility
- Handle IG 438+'s account switcher via `content-desc` fallback matching, since the previous selector no longer matches the current layout
- Handle Instagram's follower-list restriction gracefully instead of crashing when a target's list is rate-limited
- Detect and skip sponsored/ad posts in the feed instead of mishandling them
- Fixed post likers list opening the wrong profile: `open_likers_container()` was misclicking the first liker's avatar/username instead of opening the full likers list — fixed in both the primary selector path and the XML-hierarchy compatibility fallback
- Fixed stricter photo/video detection: a `video_container` element alone is no longer enough to classify a post as a video, since photo posts on current IG also carry overlay badges matching that element. A post is now only classified as video if a play button or timer is present too — closes #5
- Fixed back-navigation overshoot after opening a post: replaced a fixed-count back-press assumption with a state check (stop once the profile tab bar is visible again, capped at 3 presses), preventing the bot from overshooting back to the blogger's likers list between posts
- Fixed `_check_if_last_post()` hanging indefinitely (sometimes for hours) on collab/repost posts where the caption is attributed to a different account than the profile owner — added a retry cap and a graceful fallback
- Fixed posts with undetectable media type (`MediaType.UNKNOWN`) being silently skipped by the like logic instead of falling back to the standard like flow
- Reworked unfollow-from-list to use the current three-dots options menu instead of a now-removed direct "Following" button; accounts with no Unfollow option available are now collected and reported via Telegram at the end of a run instead of being logged as crashes

### Stability
- Fixed `DeviceFacade.is_alive()` throwing `AttributeError` on current `uiautomator2` (`_is_alive()` and `.server.alive` were both removed upstream) — replaced with a functional check against `.info`
- Fixed a narrow `except uiautomator2.JSONRPCError` clause throwing its own `AttributeError` and masking the real underlying error, since `JSONRPCError` is no longer a valid top-level attribute on current `uiautomator2`

### Setup & packaging
- Package directory fully renamed from `GramAddict` to `InstaAddict`
- Account folders now auto-created from `config-examples/` on first run instead of requiring manual setup
- `requirements.txt`: added `imageio` and `websocket-client` (previously undeclared runtime dependencies), and resolved `setuptools`/`pkg_resources` breakage on Python 3.13

**Full diff**: `v1.0.1...v1.0.2`

## 1.0.1 (2026-07-18) - First InstaAddict Release

This is the first production release of **InstaAddict**, a continuation of the [GramAddict](https://github.com/GramAddict/bot) project.

### New
- Forked and rebranded from GramAddict to InstaAddict
- Updated to support Instagram version 438.0.0.28.88
- Updated profile header resource IDs to match new Instagram UI (posts, followers, following counts)
- Added support for new `profile_header_familiar_*` resource ID patterns
- Updated `.gitignore` to properly exclude sensitive account configs, crash dumps, and logs

### Changed
- All user-facing branding changed from GramAddict to InstaAddict
- GitHub references updated to `https://github.com/joeahkim/InstaAddict`
- Version reset to 1.0.1 for the InstaAddict fork

---

## Previous InstaAddict Releases

## 3.2.12 (2024-03-22)
### Fix
- handle NoneType for owner_name in feel job
- wrong indentation for hashtag check in feed job
## 3.2.11 (2024-03-17)
## New Features
- OCR to read the post owner if the obj is missing in the feed job (optional)
- `restart-atx-agent: bool` to restart the atx-agent before starting the bot
- `kill-atx-agent: bool` to kill the atx-agent when the script ends
### Fix
- feed sponsored detection
- Telegram wrong keys and order
## Misc
- message in telegram now looks more like it did before pandas were removed
## Test
- improved telegram test
## 3.2.10 (2024-03-09)
### Fix
- account selecting
- function specialization for load and clean txt file
- better logging for the user
### Others
- test for load and clean txt file
## 3.2.9 (2024-02-10)
### Fix
- remove pandas as dependency for telegram reports
- show when config file and filter file have been saved
- better logging information
## 3.2.8 (2024-01-24)
### Fix
- removed the language check
## 3.2.7 (2023-09-30)
### Fix
- using the monkey approach until this bug is fixed https://github.com/openatx/atx-agent/pull/111
## 3.2.6 (2023-09-28)
### Fix
- get rid of Activity class when starting app
## 3.2.5 (2023-07-23)
### Fix
- account selection with the little arrow instead of clicking on the account name
### Others
- display a warning if the user tries to use an untested version of IG
## 3.2.4 (2023-04-07)
### Fix
- fix selecting account if you have a lof of them, and it's not visible
- screen timeout checking for 'always on devices' (for example emulators)
### Others
- config loader in 'extra' folder
## 3.2.3 (2022-06-23)
### Others
- allow to pass device to dump
- allot to don't to kill the demon while dumping
## 3.2.2 (2022-04-28)
### Fix
- deprecated method uiautomator2 side that cause that error:
  >AttributeError: 'Session or Device' object has no attribute '_is_alive'
## 3.2.1 (2022-03-25)
### Fix
- default value for `unfollow-delay` was an integer instead of a string
- story_watcher returned Optional\[Union\[bool, int]] instead of int
## 3.2.0 (2022-03-23)
### New Features
- `unfollow` and `unfollow-non-followers` now check for when you last interacted with each user. Using the argument `unfollow-delay` you can specify the number of days that have to have passed since the last interaction
- after watching a story, the bot will now like it
- with `count-app-crashes` you can tell the bot to count app crashes as a crash for `total-crashes-limit` (default False)
- using the argument `remove-followers-from-file`, the bot can now remove followers following you from a *.txt
### Fix
- when interacting with the last picture of a profile, the bot could crash
- following suggested people instead of target account
- missing block detection for full screen mode (video)
- profile is loaded false negative
- avoid re-watching content if like fails
### Performance improvements
- new way to search for targets in search menu
- no need to see limits for PM if you're not sending them
- code has been cleaned and some functions have been merged
- inspect current view for list of users, this will avoid pressing on bottom bar
- set the screen timeout to 5 minutes if it's less than this value to avoid screen off issues
- store the target source in json instead of a duplicate of the username
- store request and followed status in json (it uses to be only followed)
- using `app_current` instead `info` for checking if the app is opened
- check for crash dialog when app crashes
- check if it's a live video before opening a story
- for actions with files (`interact-from-file`, `unfollow-form-file` and `remove-followers-from-file`) the script will look inside your account folder and no longer where you start the bot from
### Others
- bump version of UIA2
- trim logs in crash reports
- put your username inside the config when creating it with `gramaddict init username`
- default value for `can-reinteract-after` is now "None" instead of "-1"
- better logs when skipping profiles
## 3.1.5 (2022-02-07)
### Fix
- `app_id` was None for them who used the tool in a fancy way (without using config files)
## 3.1.4 (2022-02-07)
### Fix
- avoid a problem with `check_if_crash_popup_is_there` and `choose_cloned_app` being decorated before starting IG
## 3.1.3 (2022-02-06)
### Fix
- missing parenthesis in calling a method
## 3.1.2 (2022-02-06)
### Fix
- find the profile icon even with the different interface
- wrong arguments for stop_bot function
- workaround for avoiding story watching crash due to a bug of UIA2
### Performance improvements
- check if IG is opened when we try to find an element, raise an exception if it's not true (I used a decorator, for fun :D)
- simplify some functions
### Others
- move close_keyboard method to universal class
- a lot of typos
- some types hint
## 3.1.1 (2022-02-01)
### Fix
- inconsistent way to store datetime in json
## 3.1.0 (2022-01-31)
### New Features
- new argument `dont-type` allows writing text by pasting it instead of typing it
- you can go next line in your PM by adding `\n` in the text
### Fix
- the bot wasn't able to confirm the like if the button was not visible in the view
### Others
- don't show countdown in debug mode
## 3.0.5 (2022-01-26)
### Fix
- avoid pressing on music tab instead of hashtags (this bug was only for small screens)
### Others
- the bot restarts after a crash, except for some scenarios that will be highlighted
## 3.0.4 (2022-01-17)
### Fix
- carousel mid-point calculation was wrong (typo)
## 3.0.3 (2022-01-17)
### Fix
- in the new version (217..) the element for sorting following list has changed
### Performance improvements
-  better info when min-following is used in unfollow actions, or you're trying to unfollow more people than the number you're following
-  handle of malformed data in telegram-reports
## 3.0.2 (2022-01-10)
### Fix
- "back" in "Follow Back" is not uppercase anymore
### Performance improvements
- better handling for not loaded profiles
## 3.0.1 (2022-01-05)
### Fix
- missing argument in analytics report

### Others
- new logo for the readme.md
- added some useful info for the user

## 3.0.0 (2022-01-05)
### New Features

- use the cloned app instead the official, if the dialog box get displayed (this is currently supporter for MIUI devices)
- new filter options: *interact_if_public* and *interact_if_private*
- *interact_only_private* has been removed, delete it from your filters.yml

### Performance improvements

- limit check was wrong in interact_blogger plugin
- feed job was ignoring limits
- don't throw an error if config files \*.yaml instead of \*.yml are used
- likes_limit was referring to total_likes_limit and not current_likes_limit (that caused an error if you specify an interval)

### Performance improvements

- jobs have been split in "active-" and "unfollow-" jobs. That means, for example, that the bot won't stop the activity if it reached the likes limit, and you scheduled to unfollow.
- you can pass how many users have to be processed when working with \*.text (unfollow-from-list and interact-from-list)
- bot flow improved
- feed job improvements
- looking for description improvements
- better handle of empty biographies
- showing session ending conditions at bot start
- countdown before starting, so you can check that everything is ok (filters and ending conditions)
- before starting, the bot will tell you the filters you are going to use (there is no spell check there, if you wrote them wrong they will be displayed there but not get considered)
- disable head notifications while the bot is running
- removed unnecessary argument in check_limit function
- removed some unnecessary classes in story view
- move Filter instance outside of plugins
## 2.10.6 (2021-11-24)

#### Performance improvements

* the parsing of the number of posts / followers / following could fail for someone

Full set of changes: [`2.10.4...2.10.6`](https://github.com/InstaAddict/bot/compare/2.10.4...2.10.6)
## 2.10.5 (2021-11-18)

#### Fixes

* 'NoneType' object has no attribute '_is_post_liked'
#### Others

* removed a typo

Full set of changes: [`2.10.4...2.10.5`](https://github.com/InstaAddict/bot/compare/2.10.4...2.10.5)

## 2.10.4 (2021-11-08)

#### Fixes

* scraped is now counted as successful interaction

Full set of changes: [`2.10.3...2.10.4`](https://github.com/InstaAddict/bot/compare/2.10.3...2.10.4)

## 2.10.3 (2021-11-06)

#### Fixes

* the bot did not inform about the skip in case of the filter on mutual friends or on the link in bio
* false positive for link check in bio

Full set of changes: [`2.10.2...2.10.3`](https://github.com/InstaAddict/bot/compare/2.10.2...2.10.3)

## 2.10.2 (2021-11-06)

#### Fixes

* link in bio object exists even if it's empty

Full set of changes: [`2.10.1...2.10.2`](https://github.com/InstaAddict/bot/compare/2.10.1...2.10.2)

## 2.10.1 (2021-10-31)

#### Fixes

* someone in the world has a " ’ " as thousands separator instead of " , "

Full set of changes: [`2.10.0...2.10.1`](https://github.com/InstaAddict/bot/compare/2.10.0...2.10.1)

## 2.10.0 (2021-10-27)

#### New Features

* you can control if comment carousels
* support for connect_adb_wifi uia2 method
* support for watching videos and check for already liked posts
#### Fixes

* trying to close the android pop-up if ig crashes
* looking for the like button on the following video instead of the one being played
* comment fails on some media types
* checking media_type could fail
* empty files in unfollow from list job
* unfollow from list loop
* removed unexpected keyword argument in getFollowinCount method
* method connect_adb_wifi contained some errors
* was being imported nan by numpy instead of the math module
* ig is not opened but the bot tries to do operations
#### Performance improvements

* video recording
* posts-from-file job improved and fixed
* little improvements to the module mode

Full set of changes: [`2.9.2...2.10.0`](https://github.com/InstaAddict/bot/compare/2.9.2...2.10.0)

## 2.9.2 (2021-10-06)

#### Fixes

* other incompatibilities in the latest IG version

Full set of changes: [`2.9.1...2.9.2`](https://github.com/InstaAddict/bot/compare/2.9.1...2.9.2)

## 2.9.1 (2021-10-06)

#### New Features

* module version thanks to @patbengr
* if a username in *.txt file is not found, it will be appended to a *_not_found.txt
* from now, you can customize the session ending conditions
#### Fixes

* compatibility with IG: 208.0.0.32.135
* cannot check the language of Ig if not at the top of the account
* handle an exception in case you start the bot without specifying the config file
* it could happen that you are not at the top of your main profile in some circumstances
#### Performance improvements

* clean code for open and close ig

Full set of changes: [`2.9.0...2.9.1`](https://github.com/InstaAddict/bot/compare/2.9.0...2.9.1)

## 2.9.0 (2021-08-25)

#### New Features

* new argument to control how many skips in jobs with posts (e.g.: hashtag-post-top) are allowed before moving to another source / job
* new job to unfollow people who are following you
* new filter for skipping accounts with banned biography language
#### Performance improvements

* improved readability of the code and correct some typos
* moving sibling folders of run.py will no longer executed automatically

Full set of changes: [`2.8.0...2.9.0`](https://github.com/InstaAddict/bot/compare/2.8.0...2.9.0)

## 2.8.0 (2021-08-04)

#### New Features

* new filters: 'skip_if_link_in_bio: true/false' and 'mutual_friends: a_number' min count
* new feature added: pre- and post-script execution

Full set of changes: [`2.7.7...2.8.0`](https://github.com/InstaAddict/bot/compare/2.7.7...2.8.0)

## 2.7.7 (2021-08-03)

#### Fixes

* place first post not found [#208](https://github.com/InstaAddict/bot/issues/208)
* replace detect-block with disable-block-detection
#### Performance improvements

* removed unneeded class and sort imports

Full set of changes: [`2.7.6...2.7.7`](https://github.com/InstaAddict/bot/compare/2.7.6...2.7.7)

## 2.7.6 (2021-07-31)

#### Fixes

* missing resource id for sorting following list

Full set of changes: [`2.7.5...2.7.6`](https://github.com/InstaAddict/bot/compare/2.7.5...2.7.6)

## 2.7.5 (2021-07-30)

#### New Features

* new argument "detect_block: true/false" to enable/ disable block check after every action
#### Fixes

* a better way to sort following list [#207](https://github.com/InstaAddict/bot/issues/207)
#### Performance improvements

* add debug info for swipes
#### Refactorings

* sort imports

Full set of changes: [`2.7.4...2.7.5`](https://github.com/InstaAddict/bot/compare/2.7.4...2.7.5)

## 2.7.4 (2021-07-25)

#### Fixes

* support for Ig v. 197.0.0.26.119

Full set of changes: [`2.7.3...2.7.4`](https://github.com/InstaAddict/bot/compare/2.7.3...2.7.4)

## 2.7.3 (2021-07-14)

#### Fixes

* sometimes the bot press on 'Switch IME' instead of open your profile
* automatic change in English locale stopped working

Full set of changes: [`2.7.2...2.7.3`](https://github.com/InstaAddict/bot/compare/2.7.2...2.7.3)

## 2.7.2 (2021-07-14)

#### Fixes

* bug in open post container when someone in your 'following list' has also liked the post
#### Performance improvements

* lowered a little the swipe up in sorting `Following accounts`

Full set of changes: [`2.7.1...2.7.2`](https://github.com/InstaAddict/bot/compare/2.7.1...2.7.2)

## 2.7.1 (2021-07-13)

#### New Features

* you can dump your current screen with that command `gramaddict dump`
#### Performance improvements

* we don't need to click on an obj if we are already on it

Full set of changes: [`2.7.0...2.7.1`](https://github.com/InstaAddict/bot/compare/2.7.0...2.7.1)

## 2.7.0 (2021-07-12)

#### New Features

* you can use spintax for comments and PM from now
#### Fixes

* forgot to remove 'time_left' when calling print_telegram_reports at the end of all sessions
* in config-examples forgot 'comment_blogger' and fix typo in 'comment_blogger_following'

Full set of changes: [`2.6.5...2.7.0`](https://github.com/InstaAddict/bot/compare/2.6.5...2.7.0)

## 2.6.5 (2021-07-06)

#### Fixes

* the count of items in the carousels stopped at the first match
* from now on, every type of interaction is counted as successful and not just likes

Full set of changes: [`2.6.4...2.6.5`](https://github.com/InstaAddict/bot/compare/2.6.4...2.6.5)

## 2.6.4 (2021-07-01)

#### Fixes

* telegram-reports when out of working hours crashed
#### Performance improvements

* improve update checking
#### Docs

* text improvement and typo corrections

Full set of changes: [`2.6.3...2.6.4`](https://github.com/InstaAddict/bot/compare/2.6.3...2.6.4)

## 2.6.3 (2021-06-26)

#### Fixes

* time left in telegram-reports was wrong

Full set of changes: [`2.6.2...2.6.3`](https://github.com/InstaAddict/bot/compare/2.6.2...2.6.3)

## 2.6.2 (2021-06-25)

#### Fixes

* there was a problem with likers list
* there was a problem with the way I moved the reports at the end of sessions
#### Performance improvements

* the bot can recognize hashtag suggestions in feed
* telegram-reports improved
#### Docs

* typo in readme

Full set of changes: [`2.6.1...2.6.2`](https://github.com/InstaAddict/bot/compare/2.6.1...2.6.2)

## 2.6.1 (2021-06-24)

#### Performance improvements

* we can use an entry point from now
#### Docs

* correct a typo in telegram-reports
* improved the README

Full set of changes: [`2.6.0...2.6.1`](https://github.com/InstaAddict/bot/compare/2.6.0...2.6.1)

## 2.6.0 (2021-06-24)

#### New Features

* you can run InstaAddict from the command line for initializing your account folder with all the files needed
* add support for allow re-interaction after a given amount of hours
#### Fixes

* too many `filters.yml is not loaded`
* telegram-reports typo in report
* add support for viewers count where likes count is missing
* browse the carousel could fail in some circumstances
#### Docs

* completely rewrote the README.md
#### Others

* donation alert when bot stops by pressing CTRL+C
