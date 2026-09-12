import yaml

with open('agent/progress.yaml', 'r') as f:
    data = yaml.safe_load(f)

data['project']['current_milestone'] = None
data['project']['status'] = 'milestone_completed'
data['project']['description'] = 'Human-like Instagram automation bot powered by ADB and UIAutomator2. Features content queue upload pipeline and IG v446+ compatibility.'

with open('agent/progress.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
    
print("Updated project status.")
