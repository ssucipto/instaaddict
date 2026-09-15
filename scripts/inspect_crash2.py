import zipfile
import re

z = "crashes/1.0.2_2026-09-12-14-10-03.zip"
with zipfile.ZipFile(z, "r") as zip_ref:
    for f in zip_ref.namelist():
        if f.endswith(".xml"):
            xml = zip_ref.read(f).decode("utf-8", errors="ignore")
            # find action bar related things
            # lolatheozjack should be on the screen somewhere
            print("Is lolatheozjack on screen?", "lolatheozjack" in xml.lower())
            match = re.search(r'<node[^>]*text=\"lolatheozjack\"[^>]*>', xml, re.IGNORECASE)
            if match:
                print("Username node:", match.group(0))
            else:
                match = re.search(r'<node[^>]*content-desc=\"lolatheozjack\"[^>]*>', xml, re.IGNORECASE)
                if match:
                    print("Username node (desc):", match.group(0))
            
            # Print recent nodes that might be a title
            ids = set(re.findall(r'resource-id=\"([^\"]+)\"', xml))
            print("Resource IDs present in crash dump header:", [r for r in ids if "title" in r.lower() or "action_bar" in r.lower()])
