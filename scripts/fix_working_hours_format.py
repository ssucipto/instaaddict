import yaml

with open('accounts/<your-account>/config.yml', 'r') as f:
    config = yaml.safe_load(f)

# Python's strptime %H format only supports 00-23
config['working-hours'] = "00.00-23.59"

with open('accounts/<your-account>/config.yml', 'w') as f:
    yaml.dump(config, f, sort_keys=False, width=1000)
