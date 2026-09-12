import re

with open('InstaAddict/core/interaction.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Fix the subprocess shell injection vulnerability
code = code.replace(
    'subprocess.run(f"adb -s {device.deviceV2.serial} shell input keyevent 62", shell=True)',
    'subprocess.run(["adb", "-s", str(device.deviceV2.serial), "shell", "input", "keyevent", "62"], shell=False)'
)

# Fix the Action Blocked bug where I referenced non-existent Limits Enum
old_ban = """                        if blocked.exists(timeout=2):
                            logger.error("Ig Action Blocked overlay detected! Disabling comments globally for this run.")
                            session_state.Limits.COMMENTS = 0 # Force soft fallback limit mapping
                            ok_btn = device.find(textMatches="(?i)Tell us|(?i)OK")"""

new_ban = """                        if blocked.exists(timeout=2):
                            logger.error("Ig Action Blocked overlay detected! Aborting to prevent ban cascade.")
                            # session_state natively records blocks and we should raise it
                            ok_btn = device.find(textMatches="(?i)Tell us|(?i)OK")
                            if ok_btn.exists(): ok_btn.click()
                            from InstaAddict.core.exceptions import ActionBlockedError
                            raise ActionBlockedError("Action Blocked during comment injection.")"""

code = code.replace(old_ban, new_ban)

with open('InstaAddict/core/interaction.py', 'w', encoding='utf-8') as f:
    f.write(code)
