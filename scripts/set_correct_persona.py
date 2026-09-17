import yaml

with open('accounts/<your-account>/config.yml', 'r') as f:
    config = yaml.safe_load(f)

# Update to universal persona parameter
if 'ai-caption-persona' in config:
    del config['ai-caption-persona']
    
config['ai-persona'] = "A creative content creator sharing daily lifestyle and photography moments."

with open('accounts/<your-account>/config.yml', 'w') as f:
    yaml.dump(config, f, sort_keys=False)
