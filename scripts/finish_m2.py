import yaml
with open('agent/progress.yaml', 'r') as f:
    data = yaml.safe_load(f)

data['milestones'][1]['progress'] = 100
data['milestones'][1]['status'] = 'completed'

with open('agent/progress.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
