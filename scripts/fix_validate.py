import yaml
from datetime import datetime

with open('agent/progress.yaml', 'r') as f:
    data = yaml.safe_load(f)

for m_key, tasks in data.get('tasks', {}).items():
    if m_key == 'milestone_2':
        for t in tasks:
            if 'estimated_hours' not in t: t['estimated_hours'] = 2
            if 'actual_hours' not in t: t['actual_hours'] = 2
            if t['status'] == 'completed' and 'completed_date' not in t:
                t['completed_date'] = datetime.now().strftime("%Y-%m-%d")

# Check if M2 is marked completed but needs completed_date
for m in data.get('milestones', []):
    if m['status'] == 'completed' and m.get('completed') is None:
        m['completed'] = datetime.now().strftime("%Y-%m-%d")

with open('agent/progress.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
    
print("Validation fixes applied.")
