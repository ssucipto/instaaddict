import yaml

with open('agent/progress.yaml', 'r') as f:
    data = yaml.safe_load(f)

# Update tasks in M5 based on Audit 008 pre-flight
if 'tasks' in data and 'milestone_5' in data['tasks']:
    for t in data['tasks']['milestone_5']:
        if t['id'] == 'task-14':
            t['notes'] = 'Build vision_commenter.py. Implement io.BytesIO() RAM streams, Pillow 512px compression for latency, and configure BLOCK_ONLY_HIGH API safety settings.'
        elif t['id'] == 'task-16':
            t['notes'] = 'Setup python-dotenv, inject .env into .gitignore, and balance interaction limits across config.yml.'

with open('agent/progress.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
