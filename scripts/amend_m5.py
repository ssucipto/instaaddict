import yaml

with open('agent/progress.yaml', 'r') as f:
    data = yaml.safe_load(f)

# Update M5 details
for m in data.get('milestones', []):
    if m['id'] == 'M5':
        m['name'] = 'Vision-AI Engagement & Reels Stalker'
        m['notes'] = 'Implement Google Gemini Vision API for contextual commenting and activate the Reels engagement pipeline.'

# Update Tasks
if 'tasks' in data and 'milestone_5' in data['tasks']:
    for t in data['tasks']['milestone_5']:
        if t['id'] == 'task-14':
            t['name'] = 'Implement Gemini Vision AI Commenting Engine'
            t['notes'] = 'Write custom plugin to intercept comment events, screenshot UI, hit Gemini API with persona prompt, and inject contextual NLP text.'
            t['estimated_hours'] = 4
        elif t['id'] == 'task-16':
            t['notes'] = 'Update accounts/<your-account>/config.yml to include gemini-api-key, comment constraints, and Reels targeting flags.'

with open('agent/progress.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
