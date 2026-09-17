import yaml
import os

with open('agent/progress.yaml', 'r') as f:
    data = yaml.safe_load(f)

# Define M5
m5 = {
    'id': 'M5',
    'name': 'Advanced Engagement (Comments NLP & Reels Stalker)',
    'status': 'in_progress',
    'progress': 0,
    'tasks_total': 3,
    'tasks_completed': 0,
    'started': '2026-09-12',
    'notes': 'Implement spin-syntax NLP for automated commenting and activate the Reels engagement pipeline.'
}
data.get('milestones', []).append(m5)

tasks = [
    {
        'id': 'task-14', 
        'name': 'Configure NLP Spin-Syntax Commenting Engine', 
        'status': 'todo',
        'estimated_hours': 2,
        'notes': 'Generate intelligent permutations (e.g. {Great|Awesome} {shot|post}!) in a comments list and configure limits to avoid IG spam filters.'
    },
    {
        'id': 'task-15', 
        'name': 'Implement Automated Reels Stalker', 
        'status': 'todo',
        'estimated_hours': 3,
        'notes': 'Ensure bot leverages TabBarTabs.REELS, watches videos for dynamic lengths, and interacts with highly-local targets.'
    },
    {
        'id': 'task-16', 
        'name': 'Balance Configuration & Safety Limits', 
        'status': 'todo',
        'estimated_hours': 1,
        'notes': 'Update accounts/<your-account>/config.yml to include comment constraints and Reels targeting flags.'
    }
]

if 'tasks' not in data:
    data['tasks'] = {}
data['tasks']['milestone_5'] = tasks
data['project']['current_milestone'] = 'M5'
data['project']['status'] = 'in_progress'

with open('agent/progress.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)

print("Milestone 5 planned and injected into tracker.")
