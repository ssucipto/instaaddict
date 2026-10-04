---
id: route-068
title: Intelligent Contextual Commenting Engine, Sentiment-Aware Vision AI & Telemetry Modernization
task_type: feature
milestone: M11
complexity: high
executor: Antigravity
context_required:
  - agent/reports/audit-138-intelligent-contextual-commenting-and-telemetry-upgrade.md
  - agent/memory/audit-carryovers.md
files_affected:
  - InstaAddict/core/gemini_vision.py
  - InstaAddict/core/interaction.py
  - InstaAddict/core/handle_sources.py
  - InstaAddict/plugins/interact_reels.py
  - InstaAddict/core/views.py
  - InstaAddict/core/storage.py
  - test/test_intelligent_contextual_commenting.py
tokens_est: 4500
tokens_actual:
cost_est_usd:
cost_actual_usd:
created: 2026-10-04
completed: 2026-10-04
override_reason:
---

# Route-068: Intelligent Contextual Commenting Engine, Sentiment-Aware Vision AI & Telemetry Modernization

## Objectives & Scope

1. **Multimodal Context Integration (CO-114)**:
   - Expand `get_vision_comment()` and `evaluate_and_comment_reel()` to accept full multimodal context: image frame buffer, post caption, author username, and community discussion comments.
   - Update `_comment()` in `interaction.py`, `handle_sources.py`, and `interact_reels.py` to pipe the extracted caption and author username into the Vision AI generator instead of passing only raw pixels.

2. **Community Discussion Awareness (CO-115)**:
   - When the comment thread/sheet opens, inspect top 2–3 existing comments via `ROW_COMMENT_TEXTVIEW_COMMENT` or Compose node hierarchy.
   - Pass community comments to Gemini Vision to align with the room's sentiment, avoid repeating others, or react/build on existing remarks.

3. **Sentiment & Tone Classification (CO-117)**:
   - Classify post sentiment into 5 distinct operational buckets:
     * `SYMPATHETIC`: Pet passing away, illness, injury, rescue hardship (warm, comforting, gentle words).
     * `CELEBRATORY`: Birthday, gotcha day, championship, adoption, milestone (enthusiastic, joyful, cheering).
     * `PLAYFUL`: Zoomies, funny antics, goofy habits, muddy chaos (humorous, relatable, amused).
     * `INQUISITIVE`: Training questions, gear recommendations, travel spots (thoughtful, engaged).
     * `APPRECIATIVE`: Beautiful photo, sweet moment, general positive lifestyle (genuine, appreciative).
   - Enforce natural 6 to 18-word comments with subtle persona alignment, eliminating the robotic 3–6 word restriction.

4. **Safety Filter Resilience & Circuit Recovery (CO-112)**:
   - Configure Gemini safety thresholds to `BLOCK_NONE` or `BLOCK_ONLY_HIGH` across all 4 harm categories.
   - On `finish_reason=2` (Safety), automatically recover via sanitized text-only prompt re-generation or rich sentiment fallback instead of dropping out to 0 comments.

5. **Durable Comment Memory & Anti-Repetition Shield (CO-116)**:
   - Implement `CommentMemory` in `storage.py` and `gemini_vision.py` writing to `accounts/<username>/comment_history.json`.
   - Track post caption hash, target author, comment text, and sentiment.
   - Enforce Jaccard token overlap check (< 60% similarity against last 50 comments) to permanently prevent repetitive comments across sessions.

6. **Modern Instagram v447+ Compose Comment Composer (CO-113)**:
   - Fix `-32002 Client error: <> data: Selector [resourceId='com.instagram.android:id/layout_comment_thread_edittext_multiline']` by tapping the comment composer container or hint bar before invoking `set_text`.
   - Add selector cascade supporting `layout_comment_thread_edittext`, `layout_comment_thread_edittext_multiline`, and Compose `EditText`.

7. **Expanded Sentiment Fallback Library (CO-118)**:
   - Build a rich repository of 100+ dynamic spintax templates grouped by sentiment (`SYMPATHETIC`, `CELEBRATORY`, `PLAYFUL`, `APPRECIATIVE`) to replace the stale 8-line `comments_list.txt` when API is offline or throttled.

8. **Automated Verification**:
   - Create comprehensive unit test suite `test/test_intelligent_contextual_commenting.py` verifying all 7 carryovers with 100% green pass rate and zero regressions.
