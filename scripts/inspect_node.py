import re

with open("dump_screen.xml", "r", encoding="utf-8") as f:
    xml = f.read()

for node in re.findall(r'<node[^>]*row_feed_button_like[^>]*>', xml):
    print("Like Button Node:", node)

for node in re.findall(r'<node[^>]*content-desc="Like"[^>]*>', xml):
    print("Node with content-desc Like:", node)
