import yaml

with open('agent/progress.yaml', 'r') as f:
    data = yaml.safe_load(f)

# Insert task 8 right before task 9
tasks = data['tasks']['milestone_2']
task_8 = {
    'id': 'task-8',
    'name': 'Establish post publishing pipeline',
    'status': 'pending',
    'file': 'agent/tasks/milestone-2-compatibility/task-8-establish-post-pipeline.md'
}

# Find index of task-9
idx = next((i for i, t in enumerate(tasks) if t['id'] == 'task-9'), len(tasks))
tasks.insert(idx, task_8)

data['milestones'][1]['tasks_total'] = 6
data['milestones'][1]['progress'] = 50

with open('agent/progress.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
