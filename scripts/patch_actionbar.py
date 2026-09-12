import re
with open("InstaAddict/core/views.py", "r", encoding="utf-8") as f:
    code = f.read()

old_action_bar = """    def _getActionBarTitleBtn(self, watching_stories=False):
        bar = case_insensitive_re(
            [
                ResourceID.TITLE_VIEW,
                ResourceID.ACTION_BAR_TITLE,
                ResourceID.ACTION_BAR_LARGE_TITLE,
                ResourceID.ACTION_BAR_TEXTVIEW_TITLE,
                ResourceID.ACTION_BAR_TITLE_AUTO_SIZE,
                ResourceID.ACTION_BAR_LARGE_TITLE_AUTO_SIZE,
            ]
        )
        action_bar = self.device.find(
            resourceIdMatches=bar,
        )
        if not watching_stories and action_bar.exists(Timeout.LONG) or watching_stories:
            return action_bar
        logger.error(
            "Unable to find action bar! (The element with the username at top)"
        )
        return None"""

new_action_bar = """    def _getActionBarTitleBtn(self, watching_stories=False):
        bar = case_insensitive_re(
            [
                ResourceID.TITLE_VIEW,
                ResourceID.ACTION_BAR_TITLE,
                ResourceID.ACTION_BAR_LARGE_TITLE,
                ResourceID.ACTION_BAR_TEXTVIEW_TITLE,
                ResourceID.ACTION_BAR_TITLE_AUTO_SIZE,
                ResourceID.ACTION_BAR_LARGE_TITLE_AUTO_SIZE,
            ]
        )
        action_bar = self.device.find(
            resourceIdMatches=bar,
        )
        if not watching_stories and action_bar.exists(Timeout.LONG) or watching_stories:
            return action_bar
            
        # IG v446 fallback: The dedicated action bar resource IDs were removed. 
        # The title is now simply a TextView at the top of the screen containing the username.
        logger.debug("Action bar IDs not found. Falling back to layout inspection.")
        top_text = self.device.find(classNameMatches="(?i)TextView|Button", textMatches="(?i)^[-a-z0-9_.]+$")
        if top_text.exists(Timeout.SHORT):
            return top_text

        logger.error(
            "Unable to find action bar! (The element with the username at top)"
        )
        return None"""

if old_action_bar in code:
    code = code.replace(old_action_bar, new_action_bar)
    with open("InstaAddict/core/views.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("Action bar patch applied.")
else:
    print("Could not find old_action_bar block in views.py")
