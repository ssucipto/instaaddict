import sys
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

import zipfile
import re

z = "crashes/1.0.2_2026-09-12-14-10-03.zip"
with zipfile.ZipFile(z, "r") as zip_ref:
    for f in zip_ref.namelist():
        if f.endswith(".xml"):
            xml = zip_ref.read(f).decode("utf-8", errors="ignore")
            texts = re.findall(r'text=\"([^\"]+)\"', xml)
            print("Texts on screen:", [t for t in texts if len(t) > 1][:40])
            descs = re.findall(r'content-desc=\"([^\"]+)\"', xml) 
            print("Descs on screen:", [t for t in descs if len(t) > 1][:40])
