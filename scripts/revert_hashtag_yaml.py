import yaml

with open('accounts/lolatheozjack/config.yml', 'r') as f:
    config = yaml.safe_load(f)

# Revert to a single string, but separated by spaces
config['hashtag-posts-recent'] = "jackrussell dogsofinstagram doglife"

with open('accounts/lolatheozjack/config.yml', 'w') as f:
    yaml.dump(config, f, sort_keys=False, width=1000)
