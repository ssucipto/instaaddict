import re
with open("InstaAddict/plugins/upload_posts.py", "r", encoding="utf-8") as f:
    code = f.read()

# Fix the missing metavar
old_args = """        self.arguments = [
            {
                "arg": "--upload-posts",
                "nargs": None,
                "help": "Upload curated posts from accounts/<username>/content_queue/pending",
                "operation": True,
            }
        ]"""
new_args = """        self.arguments = [
            {
                "arg": "--upload-posts",
                "help": "Upload curated posts from accounts/<username>/content_queue/pending",
                "action": "store_true",
                "operation": True,
            }
        ]"""
        
code = code.replace(old_args, new_args)

with open("InstaAddict/plugins/upload_posts.py", "w", encoding="utf-8") as f:
    f.write(code)
