import os
os.makedirs("accounts/<your-account>/content_queue/pending", exist_ok=True)
os.makedirs("accounts/<your-account>/content_queue/published", exist_ok=True)
print("Content queues created.")
