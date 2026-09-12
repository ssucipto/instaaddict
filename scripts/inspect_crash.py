import zipfile
import os
import re

z = "crashes/1.0.2_2026-09-12-12-12-35.zip"
if os.path.exists(z):
    with zipfile.ZipFile(z, "r") as zip_ref:
        print("Files in dump:", zip_ref.namelist())
        for f in zip_ref.namelist():
            if f.endswith(".xml"):
                content = zip_ref.read(f).decode("utf-8", errors="ignore")
                texts = re.findall(r'text="([^"]+)"', content)
                content_descs = re.findall(r'content-desc="([^"]+)"', content)
                print("UI Texts:", [t for t in texts if len(t) > 1][:25])
                print("UI Content-Descs:", [c for c in content_descs if len(c) > 1][:25])
