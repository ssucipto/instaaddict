import yaml

with open('accounts/<your-account>/config.yml', 'r') as f:
    config = yaml.safe_load(f)

# Activate Comments natively
config['comment-percentage'] = "15-30"
config['max-comments-pro-user'] = 1
config['total-comments-limit'] = "10-15"

with open('accounts/<your-account>/config.yml', 'w') as f:
    yaml.dump(config, f, sort_keys=False)
