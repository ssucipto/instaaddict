# Reusable Code Patterns
# Populated automatically by /acp-commit when patterns are identified
# Format: date-stamped YAML entries, max 60 days active

- date: 2026-09-15
  name: vlm-retry-backoff-and-job-prioritization
  description: "Wrap multimodal VLM requests in a 5-attempt retry loop with exponential delay on 500/503/504 errors and prioritize upload jobs at the head of execution queues to eliminate starvation from downstream interaction crashes."
  context: "Vision AI inference on Google Gemini models and scheduled content publishing in bot automation systems."
  solution: "In gemini_vision.py, catch transient Google API timeouts and retry with progressive sleep. In bot_flow.py, dynamically relocate upload-posts to jobs_list[0] before randomizing subsequent interaction tasks."
