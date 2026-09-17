import yaml

with open('accounts/<your-account>/config.yml', 'r') as f:
    config = yaml.safe_load(f)

if 'upload-posts' not in config:
    config['upload-posts'] = True

with open('accounts/<your-account>/config.yml', 'w') as f:
    yaml.dump(config, f, sort_keys=False)
