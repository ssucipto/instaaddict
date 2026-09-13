import yaml

with open('agent/progress.yaml', 'r') as f:
    config = yaml.safe_load(f)

handoff = config.get('active_handoff')
if handoff:
    print(handoff.get('path'))
else:
    print('None')
