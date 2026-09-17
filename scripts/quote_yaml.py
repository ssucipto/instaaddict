import yaml

with open('accounts/<your-account>/config.yml', 'r') as f:
    config = yaml.safe_load(f)

config['ai-persona'] = "A creative content creator sharing daily lifestyle and photography moments."

with open('accounts/<your-account>/config.yml', 'w') as f:
    # Use explicit double quotes for this string so argparse doesn't break
    yaml.dump(config, f, sort_keys=False, default_style='"')
