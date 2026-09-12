import yaml

with open('agent/progress.yaml', 'r') as f:
    data = yaml.safe_load(f)

# Update tasks in M5 based on Deep Dive Audit 012 (Fifth Round)
if 'tasks' in data and 'milestone_5' in data['tasks']:
    for t in data['tasks']['milestone_5']:
        if t['id'] == 'task-14':
            t['notes'] += ' NEWv5: Inject temperature=0.9 for creative entropy. Add raw Spacebar keyevent (62) trick to wake up React Native UI listeners. Hardcode session killswitch at 50 API calls to prevent billing traps.'

with open('agent/progress.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
