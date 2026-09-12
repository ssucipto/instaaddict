import yaml

try:
    with open('agent/progress.yaml', 'r') as f:
        data = yaml.safe_load(f)
    print("YAML is valid.")
    
    # Check fields based on standard ACP schema
    for m in data.get('milestones', []):
        if 'id' not in m or 'name' not in m or 'status' not in m:
            print(f"Milestone {m.get('id')} missing required fields.")
            
    for m_key, tasks in data.get('tasks', {}).items():
        for t in tasks:
            if 'id' not in t or 'name' not in t or 'status' not in t:
                print(f"Task {t.get('id')} missing required fields.")
except Exception as e:
    print(f"Validation failed: {e}")
