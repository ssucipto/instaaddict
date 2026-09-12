import yaml

with open('accounts/lolatheozjack/config.yml', 'r') as f:
    config = yaml.safe_load(f)

# The loaded config dictionary will successfully read the multiline string natively natively.
# We just need to dump it back out enforcing no line-wrapping!

with open('accounts/lolatheozjack/config.yml', 'w') as f:
    yaml.dump(config, f, sort_keys=False, width=1000)
