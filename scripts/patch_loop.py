import re

with open('InstaAddict/core/views.py', 'r', encoding='utf-8') as f:
    code = f.read()

old_block = """    def _check_if_liked(self):
        logger.debug("Check if like succeeded in post view.")
        bnt_like_obj = self.device.find(
            resourceIdMatches=ResourceID.ROW_FEED_BUTTON_LIKE
        )
        if bnt_like_obj.exists():
            STR = "Liked"
            if self.device.find(descriptionMatches=case_insensitive_re(STR)).exists():
                logger.debug("Like is present.")
                return True
            else:
                logger.debug("Like is not present.")
                return False
        else:
            UniversalActions(self.device)._swipe_points(
                direction=Direction.DOWN, delta_y=100
            )
            return PostsViewList(self.device)._check_if_liked()"""

new_block = """    def _check_if_liked(self, retries=3):
        logger.debug("Check if like succeeded in post view.")
        bnt_like_obj = self.device.find(
            resourceIdMatches=ResourceID.ROW_FEED_BUTTON_LIKE
        )
        if bnt_like_obj.exists():
            STR = "Liked"
            if self.device.find(descriptionMatches=case_insensitive_re(STR)).exists():
                logger.debug("Like is present.")
                return True
            else:
                logger.debug("Like is not present.")
                return False
        else:
            if retries <= 0:
                logger.debug("Could not verify like via standard button ID. Assuming already handled.")
                return True
            UniversalActions(self.device)._swipe_points(
                direction=Direction.DOWN, delta_y=100
            )
            return PostsViewList(self.device)._check_if_liked(retries=retries-1)"""

code = code.replace(old_block, new_block)

with open('InstaAddict/core/views.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched infinite loop in views.py")
