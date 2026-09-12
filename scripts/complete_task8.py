import yaml

with open('agent/progress.yaml', 'r') as f:
    data = yaml.safe_load(f)

for t in data['tasks']['milestone_2']:
    if t['id'] == 'task-8':
        t['status'] = 'completed'

data['milestones'][1]['tasks_completed'] = 5
data['milestones'][1]['progress'] = 83

with open('agent/progress.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
