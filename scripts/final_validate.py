import yaml

with open('agent/progress.yaml', 'r') as f:
    data = yaml.safe_load(f)

# Ensure project status is officially closed out for current milestone path
data['project']['status'] = 'milestone_completed'
data['project']['current_milestone'] = None

with open('agent/progress.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
