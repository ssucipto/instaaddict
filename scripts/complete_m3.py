import yaml
from datetime import datetime

with open('agent/progress.yaml', 'r') as f:
    data = yaml.safe_load(f)

for m in data.get('milestones', []):
    if m['id'] == 'M3':
        m['status'] = 'completed'
        m['progress'] = 100
        m['completed'] = datetime.now().strftime("%Y-%m-%d")
        m['tasks_completed'] = 3

if 'milestone_3' in data.get('tasks', {}):
    for t in data['tasks']['milestone_3']:
        t['status'] = 'completed'
        t['completed_date'] = datetime.now().strftime("%Y-%m-%d")
        
data['project']['status'] = 'milestone_completed'
data['project']['current_milestone'] = None

with open('agent/progress.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
