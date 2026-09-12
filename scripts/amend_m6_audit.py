import yaml

with open('agent/progress.yaml', 'r') as f:
    data = yaml.safe_load(f)

# Update tasks in M6 based on Deep Dive Audit 014
if 'tasks' in data and 'milestone_6' in data['tasks']:
    for t in data['tasks']['milestone_6']:
        if t['id'] == 'task-17':
            t['notes'] = 'Architect Vision-Captioning Bridge. NEW: Bifurcate MIME types to handle .mp4 via genai.upload_file(). Inject a new yaml config parameter `ai-caption-persona` to allow customized dynamic system prompts. Forbid @mentions and strip markdown.'
        elif t['id'] == 'task-18':
            t['notes'] += ' Ensure regex sanitizer cleans up AI payload (stripping formatting artifacts like *) before injecting via UIAutomator2.'

with open('agent/progress.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
