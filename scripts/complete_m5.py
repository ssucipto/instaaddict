import yaml
with open('agent/progress.yaml', 'r') as f:
    data = yaml.safe_load(f)

# Record M5
for m in data.get('milestones', []):
    if m['id'] == 'M5':
        m['status'] = 'completed'
        m['progress'] = 100
        m['completed'] = '2026-09-12'
        m['tasks_completed'] = 3

if 'tasks' in data and 'milestone_5' in data['tasks']:
    for t in data['tasks']['milestone_5']:
        t['status'] = 'completed'
        t['completed_date'] = '2026-09-12'

data['project']['status'] = 'milestone_completed'

with open('agent/progress.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
