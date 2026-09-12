import yaml

with open('agent/progress.yaml', 'r') as f:
    data = yaml.safe_load(f)

# Define M3
m3 = {
    'id': 'M3',
    'name': 'Uploader Stabilization & UI State Validation',
    'status': 'in_progress',
    'progress': 0,
    'tasks_total': 3,
    'tasks_completed': 0
}
data.get('milestones', []).append(m3)

tasks = [
    {'id': 'task-10', 'name': 'Fix ADB subprocess bridge', 'status': 'todo'},
    {'id': 'task-11', 'name': 'Implement strict media extensions', 'status': 'todo'},
    {'id': 'task-12', 'name': 'Validate Share UI phase', 'status': 'todo'}
]
data.setdefault('tasks', {})['milestone_3'] = tasks
data['project']['current_milestone'] = 'M3'
data['project']['status'] = 'in_progress'

with open('agent/progress.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
