import yaml
try:
    with open('agent/progress.yaml', 'r') as f:
        data = yaml.safe_load(f)
    print("progress.yaml parsed successfully")
except Exception as e:
    print(f"Error parsing progress.yaml: {e}")
