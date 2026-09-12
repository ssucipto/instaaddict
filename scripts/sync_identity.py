import yaml

with open('agent/core/identity.yml', 'r') as f:
    data = yaml.safe_load(f)

if 'capabilities' not in data:
    data['capabilities'] = []

if 'IG v446+ Compatibility' not in data['capabilities']:
    data['capabilities'].extend([
        'IG v446+ Compatibility (Action Bar & Media group resolution)',
        'Local JSON/Media queue processing (UploadPostsPlugin)'
    ])

with open('agent/core/identity.yml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
print("Synced identity.yml with new capabilities.")
