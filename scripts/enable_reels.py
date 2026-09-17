import yaml

with open('accounts/<your-account>/config.yml', 'r') as f:
    config = yaml.safe_load(f)

# Activate Reels natively
config['interact-reels'] = "10-20"
config['end-if-comments-limit-reached'] = False # Disable hard-stop to let reels stalker finish

with open('accounts/<your-account>/config.yml', 'w') as f:
    yaml.dump(config, f, sort_keys=False)
