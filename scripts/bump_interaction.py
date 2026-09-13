import yaml

with open('accounts/lolatheozjack/config.yml', 'r') as f:
    config = yaml.safe_load(f)

# The user wants to engage more
config['interact-percentage'] = '80-100'
config['comment-percentage'] = '40-60' # Bumped due to awesome AI
config['likes-percentage'] = '100'

with open('accounts/lolatheozjack/config.yml', 'w') as f:
    yaml.dump(config, f, sort_keys=False, width=1000)
