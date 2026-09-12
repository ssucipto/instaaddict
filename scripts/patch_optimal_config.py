import yaml

with open('accounts/lolatheozjack/config.yml', 'r') as f:
    config = yaml.safe_load(f)

# The core loops & limits
config['total-sessions'] = -1
config['working-hours'] = ['09-22']
config['repeat'] = '120-180'
config['analytics'] = True

# Increase outreach limits natively
config['total-likes-limit'] = '25-40'
config['total-successful-interactions-limit'] = '30-45'
config['total-interactions-limit'] = '50-70'

# Follow & Unfollow Logic matching
config['follow-percentage'] = 20
config['total-follows-limit'] = '15-20'
config['total-unfollows-limit'] = '20-40'
config['unfollow-non-followers'] = '15-30'
config['unfollow-delay'] = 3

# Inject diversification
config['hashtag-posts-recent'] = ['jackrussell', 'dogsofinstagram', 'doglife']

with open('accounts/lolatheozjack/config.yml', 'w') as f:
    yaml.dump(config, f, sort_keys=False)
    
print("Successfully patched accounts/lolatheozjack/config.yml.")
