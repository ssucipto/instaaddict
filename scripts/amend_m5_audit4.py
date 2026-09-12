import yaml

with open('agent/progress.yaml', 'r') as f:
    data = yaml.safe_load(f)

# Update tasks in M5 based on Deep Dive Audit 011 (Fourth Round)
if 'tasks' in data and 'milestone_5' in data['tasks']:
    for t in data['tasks']['milestone_5']:
        if t['id'] == 'task-14':
            t['notes'] += ' NEWv4: Implement Global Circuit Breaker for dead APIs. Re-order execution (Screenshot BEFORE opening comment modal). Handle "Action Blocked" popups gracefully by disabling session commenting.'
        elif t['id'] == 'task-15':
            t['notes'] += ' NEWv4: Implement UI State Hashing (Username lock). If Reel shifts during API delay, abort injection to prevent catastrophic context mismatch.'

with open('agent/progress.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
