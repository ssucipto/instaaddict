import yaml

with open('agent/progress.yaml', 'r') as f:
    data = yaml.safe_load(f)

# Add Task 9 for Action Bar
task_9 = {
    'id': 'task-9',
    'name': 'Fix action bar title resolution for IG v446',
    'status': 'pending',
    'file': 'agent/tasks/milestone-2-compatibility/task-9-action-bar-fix.md'
}

data['tasks']['milestone_2'].append(task_9)
data['milestones'][1]['tasks_total'] = 5

with open('agent/progress.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
