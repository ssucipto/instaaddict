import yaml

with open('accounts/lolatheozjack/config.yml', 'r') as f:
    config = yaml.safe_load(f)

config['ai-caption-persona'] = "Act as Lola and Ozzie, two playful Jack Russell terrier dogs living in Sydney Australia. Talk from the dogs perspective playfully."

with open('accounts/lolatheozjack/config.yml', 'w') as f:
    yaml.dump(config, f, sort_keys=False)
