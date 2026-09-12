import yaml

with open('accounts/lolatheozjack/config.yml', 'r') as f:
    config = yaml.safe_load(f)

# Convert lists to space-separated strings block for configargparse
if isinstance(config.get('working-hours'), list):
    config['working-hours'] = " ".join(str(x) for x in config['working-hours'])

if isinstance(config.get('hashtag-posts-recent'), list):
    config['hashtag-posts-recent'] = " ".join(str(x) for x in config['hashtag-posts-recent'])

with open('accounts/lolatheozjack/config.yml', 'w') as f:
    yaml.dump(config, f, sort_keys=False)

print("Patched array structures into space-separated strings.")
