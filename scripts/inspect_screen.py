import uiautomator2 as u2
import re

d = u2.connect("emulator-5554")
curr = d.app_current()
print("App Current:", curr)
xml = d.dump_hierarchy()
with open("dump_screen.xml", "w", encoding="utf-8") as f:
    f.write(xml)

res_ids = set(re.findall(r'resource-id="([^"]+)"', xml))
print("Count of resource IDs:", len(res_ids))
like_res = [r for r in res_ids if "like" in r.lower()]
print("Like related resource IDs:", like_res)
content_descs = [c for c in re.findall(r'content-desc="([^"]+)"', xml) if "like" in c.lower()]
print("Like related content-descs:", content_descs)
media_res = [r for r in res_ids if "media" in r.lower() or "carousel" in r.lower() or "feed" in r.lower()]
print("Media/feed resource IDs:", media_res[:20])
