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

