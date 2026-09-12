import re
with open("InstaAddict/core/views.py", "r", encoding="utf-8") as f:
    code = f.read()

# Fix for CO-004: Bare exception
old_fallback = """            except Exception as e:
                pass"""
new_fallback = """            except Exception as e:
                logger.debug(f"Media child description fallback failed: {str(e)}")"""
if old_fallback in code:
    code = code.replace(old_fallback, new_fallback)

# Fix for CO-005: time.sleep(2)
old_sleep = """            if self._find_username(username):
                # Verify change
                time.sleep(2)
                action_bar = ProfileView._getActionBarTitleBtn(self)"""
new_sleep_fix = """            if self._find_username(username):
                # Verify change without hard sleep - let the _getActionBarTitleBtn UIAutomator internal wait handle it
                action_bar = ProfileView._getActionBarTitleBtn(self)"""
if old_sleep in code:
    code = code.replace(old_sleep, new_sleep_fix)

with open("InstaAddict/core/views.py", "w", encoding="utf-8") as f:
    f.write(code)
print("views.py shortcuts patched")
