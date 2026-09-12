import yaml
with open('agent/progress.yaml', 'r') as f:
    data = yaml.safe_load(f)

# Ensure milestone_2 exists in tasks
if 'milestone_2' not in data.get('tasks', {}):
    data['tasks']['milestone_2'] = []

# Add task 6 and task 7 if they aren't there
task_6 = {
    'id': 'task-6',
    'name': 'Fix media container resolution in views.py',
    'status': 'pending',
    'file': 'agent/tasks/milestone-2-compatibility/task-6-fix-media-resolution.md'
}
task_7 = {
    'id': 'task-7',
    'name': 'Prevent silent abort in like logic',
    'status': 'pending',
    'file': 'agent/tasks/milestone-2-compatibility/task-7-prevent-silent-abort.md'
}

data['tasks']['milestone_2'].extend([task_6, task_7])

with open('agent/progress.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
