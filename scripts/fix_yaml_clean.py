import yaml

with open('accounts/lolatheozjack/config.yml', 'r') as f:
    text = f.read()

# PyYAML reads it fine even with quotes.
config = yaml.safe_load(text)

with open('accounts/lolatheozjack/config.yml', 'w') as f:
    # default_style=None uses quotes ONLY when necessary (e.g. strings with strange characters)
    yaml.dump(config, f, sort_keys=False)
