import yaml

with open('accounts/lolatheozjack/config.yml', 'r') as f:
    config = yaml.safe_load(f)

# Update to universal persona parameter
if 'ai-caption-persona' in config:
    del config['ai-caption-persona']
    
config['ai-persona'] = "Lola the Oz dog. a Jack Russell terrier. she is living in Perth Western Australia."

with open('accounts/lolatheozjack/config.yml', 'w') as f:
    yaml.dump(config, f, sort_keys=False)
