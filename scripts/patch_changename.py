import re
with open("InstaAddict/core/views.py", "r", encoding="utf-8") as f:
    code = f.read()

# Make changeToUsername more resilient overall
old_change = """            if self._is_still_on_profile():
                logger.info(f"Checking if {username} account is logged in...")
                time.sleep(1)
                text = \"\"
                title = self._getActionBarTitleBtn()
                if title:
                    text = title.get_text()"""

new_change = """            if self._is_still_on_profile():
                logger.info(f"Checking if {username} account is logged in...")
                time.sleep(1)
                text = \"\"
                title = self._getActionBarTitleBtn()
                if title:
                    text = title.get_text()
                
                # Ultimate fallback - if no title was fetched, search exact text
                if not text:
                    direct_name = self.device.find(textMatches=f"(?i){username}")
                    if direct_name.exists(Timeout.SHORT):
                        logger.debug("Found username on screen despite missing action bar.")
                        text = username"""

if old_change in code:
    code = code.replace(old_change, new_change)
    with open("InstaAddict/core/views.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("changeToUsername patch applied.")
else:
    print("Could not find changeToUsername block")
