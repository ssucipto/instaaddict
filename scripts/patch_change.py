import re
with open("InstaAddict/core/views.py", "r", encoding="utf-8") as f:
    code = f.read()

# Make changeToUsername handle action_bar returning a text node or full action bar, or being None if the fallback matches directly
old_changeToUsername = """    def changeToUsername(self, username: str):
        action_bar = ProfileView._getActionBarTitleBtn(self)
        if action_bar is not None:
            current_profile_name = action_bar.get_text()
            # in private accounts there is little lock which is codec as two spaces (should be \\u1F512)
            if current_profile_name.strip().upper() == username.upper():
                logger.info(
                    f"You are already logged as {username}!",
                    extra={"color": f"{Style.BRIGHT}{Fore.BLUE}"},
                )
                return True
            logger.debug(f"You're logged as {current_profile_name.strip()}")
            selector = self.device.find(resourceId=ResourceID.ACTION_BAR_TITLE_CHEVRON)
            selector.click()
            if self._find_username(username):
                if action_bar is not None:
                    current_profile_name = action_bar.get_text()
                    if current_profile_name.strip().upper() == username.upper():
                        return True
                else:
                    logger.error(
                        "Cannot find action bar (where you select your account)!"
                    )
        return False"""

new_changeToUsername = """    def changeToUsername(self, username: str):
        action_bar = ProfileView._getActionBarTitleBtn(self)
        
        # If action_bar exists, we compare it
        if action_bar is not None:
            current_profile_name = action_bar.get_text()
            if current_profile_name and current_profile_name.strip().upper() == username.upper():
                logger.info(
                    f"You are already logged as {username}!",
                    extra={"color": f"{Style.BRIGHT}{Fore.BLUE}"},
                )
                return True
            if current_profile_name:
                logger.debug(f"You're logged as {current_profile_name.strip()}")
                
        # If no action bar was found OR names didn't match, look for dropdown selector
        selector = self.device.find(resourceId=ResourceID.ACTION_BAR_TITLE_CHEVRON)
        if not selector.exists(Timeout.SHORT):
            # Try tapping the action_bar directly as the account switcher dropdown triggers there
            if action_bar:
                selector = action_bar
        
        if selector and selector.exists():
            selector.click()
            if self._find_username(username):
                # Verify change
                time.sleep(2)
                action_bar = ProfileView._getActionBarTitleBtn(self)
                if action_bar is not None:
                    current_profile_name = action_bar.get_text()
                    if current_profile_name and current_profile_name.strip().upper() == username.upper():
                        return True
                
                # Fallback verify: search exact username on screen if action bar still failing
                direct_name = self.device.find(textMatches=f"(?i)^{username}$")
                if direct_name.exists(Timeout.SHORT):
                    return True
        else:
            # Maybe already single account and it matches? 
            # We must be on the profile already if we couldn't click a dropdown.
            direct_name = self.device.find(textMatches=f"(?i)^{username}$")
            if direct_name.exists(Timeout.SHORT):
                logger.info(f"Confirmed already logged as {username} via screen text fallback.")
                return True
                
        logger.error("Failed to switch to or verify account {username}.")
        return False"""

if old_changeToUsername in code:
    code = code.replace(old_changeToUsername, new_changeToUsername)
    with open("InstaAddict/core/views.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("changeToUsername patched.")
else:
    print("Could not find changeToUsername block")
