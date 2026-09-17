import yaml

with open('accounts/<your-account>/config.yml', 'r') as f:
    config = yaml.safe_load(f)

# Enforce Anti-Stuck & Stability Defaults
config['close-apps'] = True
config['total-crashes-limit'] = 5
config['count-app-crashes'] = True

with open('accounts/<your-account>/config.yml', 'w') as f:
    yaml.dump(config, f, sort_keys=False)

print("Enabled application state resets and crash tracking to act as a watchdog.")
