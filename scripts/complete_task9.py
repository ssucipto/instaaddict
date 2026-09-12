import yaml

with open('agent/progress.yaml', 'r') as f:
    data = yaml.safe_load(f)

for t in data['tasks']['milestone_2']:
    if t['id'] == 'task-9':
        t['status'] = 'completed'

with open('agent/progress.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
