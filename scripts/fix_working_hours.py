import yaml

with open('accounts/lolatheozjack/config.yml', 'r') as f:
    config = yaml.safe_load(f)

# The time parser in InstaAddict expects exactly "%H.%M" e.g., "09.00-22.00"
config['working-hours'] = "09.00-22.00"

with open('accounts/lolatheozjack/config.yml', 'w') as f:
    yaml.dump(config, f, sort_keys=False)

print("Patched working-hours to strict decimal format.")
