import yaml
with open('agent/progress.yaml', 'r') as f:
    data = yaml.safe_load(f)

# Record M4 (Audit/Review)
m4 = {
    'id': 'M4',
    'name': 'Security Audit & Code Quality Fixes', 
    'status': 'completed',
    'progress': 100,
    'tasks_total': 1,
    'tasks_completed': 1
}
data.get('milestones', []).append(m4)

tasks = [{'id': 'task-13', 'name': 'Address code vulnerabilities', 'status': 'completed'}]
data.setdefault('tasks', {})['milestone_4'] = tasks
data['project']['status'] = 'milestone_completed'

with open('agent/progress.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
