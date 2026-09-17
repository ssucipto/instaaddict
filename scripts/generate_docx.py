from docx import Document
from docx.shared import Pt, RGBColor
import os

doc = Document()

# Title
title = doc.add_heading('InstaAddict: Auto-Upload Step-by-Step Guide', 0)

# Intro
doc.add_paragraph(
    "The InstaAddict bot is fully configured to operate a content queue on complete autopilot. "
    "At a defined rate (by default checked once every 12-hour window during normal engagement loops), "
    "it will pull curated content directly from a local folder and post it to Instagram."
)

# Step 1
doc.add_heading('Step 1: Prep your Photos/Videos', level=2)
p1 = doc.add_paragraph()
p1.add_run("Because automated emulation cannot reliably click the tiny 'expand aspect ratio' toggle across different shifting Instagram layouts, ").italic = True
p1.add_run("Instagram will automatically crop your photo to a 1:1 Square by default.\n").bold = True
p1.add_run("Best Practice: ").bold = True
p1.add_run("Always pre-crop your .jpg or .mp4 into a perfect square (1080x1080px) on your computer before putting it into the queue to avoid your image being cut off!")

# Step 2
doc.add_heading('Step 2: Access the Payload Folder', level=2)
doc.add_paragraph("Navigate to your account's dedicated queue directory. This is where you will drop all files you want uploaded.")
doc.add_paragraph("Path: C:\\Project\\instaaddict\\instaaddict\\accounts\\<your-account>\\content_queue\\pending")

# Step 3
doc.add_heading('Step 3: Pair your Files', level=2)
doc.add_paragraph("For every individual post you want to make, you must supply two files sharing the exact same base name:")
doc.add_paragraph("1. The Image/Video: my_dog_beach.jpg")
doc.add_paragraph("2. The Caption data: my_dog_beach.json")

# Step 4
doc.add_heading('Step 4: Format the JSON properly', level=2)
doc.add_paragraph("Open your `.json` file in a raw text editor (Notepad, VS Code, etc) and write your caption explicitly in JSON format! If you want line breaks, you must use the '\\n' newline character instead of pressing Enter.")
json_code = (
    '{\n'
    '  "caption": "Had the absolute best day running around at the beach! ????? \\n\\n#pets #animals"\n'
    '}'
)
doc.add_paragraph(json_code)

# Step 5
doc.add_heading('Step 5: Fire and Forget', level=2)
doc.add_paragraph(
    "Leave the InstaAddict bot running in the background. When one of its random sleep sessions ends, "
    "it will automatically identify the newest photo pairing in the pending folder, type out your caption accurately, "
    "post it to your feed, and then instantly move the .json and .jpg files into your safely archived 'published' folder!"
)

# Limitations
doc.add_heading('Known Limitations & Workarounds', level=2)
doc.add_paragraph("Multi-Photo Carousels: ").bold = True
doc.add_paragraph("Instagram natively blocks multi-photo uploads when interacting via standard Android ADB Intents. The bot will only post single videos or single pictures.")

doc.add_paragraph("Tagging Users: ").bold = True
doc.add_paragraph("Tagging users dynamically ON the photo itself is not supported because UI tap elements shift wildly based on the picture's resolution and color saturation.")
doc.add_paragraph("Workaround: ").bold = True
doc.add_paragraph("If you want to tag someone, include their @username explicitly in your JSON caption text block! Instagram will immediately notify them that they were mentioned in your post just the same.")

doc.save(r'C:\Project\instaaddict\instaaddict\doc\export\InstaAddict_AutoUpload_Guide.docx')
print("Document Saved Successfully")
