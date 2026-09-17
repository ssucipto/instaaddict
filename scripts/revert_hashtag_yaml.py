import yaml

with open('accounts/<your-account>/config.yml', 'r') as f:
    config = yaml.safe_load(f)

# Revert to a single string, but separated by spaces
config['hashtag-posts-recent'] = "pets animals photography"

with open('accounts/<your-account>/config.yml', 'w') as f:
    yaml.dump(config, f, sort_keys=False, width=1000)
