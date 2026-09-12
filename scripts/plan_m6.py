import yaml
from copy import deepcopy

with open('agent/progress.yaml', 'r') as f:
    data = yaml.safe_load(f)

# Re-open project status
data['project']['status'] = 'in_progress'
data['project']['current_milestone'] = 'M6'

m6 = {
  'id': 'M6',
  'name': 'AI-Driven Content Generation (Autopilot Uploads)',
  'status': 'in_progress',
  'progress': 0,
  'tasks_total': 3,
  'tasks_completed': 0,
  'started': '2026-09-12',
  'notes': 'Implement Gemini Vision AI to automatically generate hyper-contextual captions and hashtag arrays for local payload uploads.'
}

if 'milestones' not in data:
    data['milestones'] = []
data['milestones'].append(m6)

if 'tasks' not in data:
    data['tasks'] = {}

data['tasks']['milestone_6'] = [
    {
        'id': 'task-17',
        'name': 'Architect Vision-Captioning Bridge',
        'status': 'todo',
        'estimated_hours': 2,
        'notes': 'Extend gemini_vision.py to support a separate "caption_generator" pipeline with a distinct persona prompt for generating IG captions + hashtags from local file arrays.'
    },
    {
        'id': 'task-18',
        'name': 'Patch UploadPostsPlugin Pipeline',
        'status': 'todo',
        'estimated_hours': 2,
        'notes': 'Intercept the image payload in upload_posts.py. If no matching .txt caption file exists alongside the image, route the image to AI, fetch caption, and pipe it to the Android UI.'
    },
    {
        'id': 'task-19',
        'name': 'Sanitization & Safety Overrides',
        'status': 'todo',
        'estimated_hours': 1,
        'notes': 'Ensure fallback logic exists (empty caption) if AI fails. Implement a custom prompt config for the specific IG profile character. Respect local .txt overrides.'
    }
]

with open('agent/progress.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
