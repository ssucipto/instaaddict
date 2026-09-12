import yaml

with open('agent/progress.yaml', 'r') as f:
    data = yaml.safe_load(f)

# Update tasks in M5 based on Deep Dive Audit 010 (Third Round)
if 'tasks' in data and 'milestone_5' in data['tasks']:
    for t in data['tasks']['milestone_5']:
        if t['id'] == 'task-14':
            t['notes'] += ' NEWv3: Apply strict max_output_tokens=15. Enforce 5.0s hard HTTP timeout to prevent ATX watchdog crashes. Mandate English linguistic locks.'
        elif t['id'] == 'task-15':
            t['notes'] += ' NEWv3: Ensure local SQLite/JSON history logs comment idempotency. NEVER double-comment on a historically matching post ID.'

with open('agent/progress.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
