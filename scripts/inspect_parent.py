import xml.etree.ElementTree as ET

tree = ET.parse("dump_screen.xml")
root = tree.getroot()

for parent in root.iter():
    for child in parent:
        if "row_feed_button_like" in child.attrib.get("resource-id", ""):
            print("PARENT:", parent.attrib)
            print("CHILD (like button):", child.attrib)
