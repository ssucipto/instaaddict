import yaml

with open('accounts/<your-account>/config.yml', 'r') as f:
    config = yaml.safe_load(f)

# The user defined it as a space separated string, converting it to a list
if isinstance(config.get('hashtag-posts-recent'), str):
    config['hashtag-posts-recent'] = config['hashtag-posts-recent'].split()

with open('accounts/<your-account>/config.yml', 'w') as f:
    yaml.dump(config, f, sort_keys=False, width=1000)
