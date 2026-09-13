import yaml

with open('agent/progress.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

config['active_handoff'] = {
    'path': 'agent/reports/handoff-human-m6-complete-2026-09-12.md',
    'date': '2026-09-12',
    'to_executor': 'human',
    'from_executor': 'antigravity',
    'git_commit': '7c50172675f78a843411f91d476ede86556abb4a',
    'status': 'active'
}

with open('agent/progress.yaml', 'w', encoding='utf-8') as f:
    yaml.dump(config, f, sort_keys=False, width=1000)
