import re
with open("InstaAddict/core/views.py", "r", encoding="utf-8") as f:
    code = f.read()

# Replace `_get_media_container` logic
old_get_media = """    def _get_media_container(self):
        media = self.device.find(resourceIdMatches=ResourceID.CAROUSEL_AND_MEDIA_GROUP)
        content_desc = media.get_desc() if media.exists() else None
        return media, content_desc"""

new_get_media = """    def _get_media_container(self):
        media = self.device.find(resourceIdMatches=ResourceID.CAROUSEL_AND_MEDIA_GROUP)
        content_desc = media.get_desc() if media.exists() else None
        
        # Fallback for IG >= v446 where contentDesc comes from its child
        if content_desc is None and media.exists():
            try:
                # Iterate actual device UI children of the media frame
                # A common hack: if the media group has no desc, one of its photo/video children does
                info = media.ui_info()
                # Find desc across immediate children via uiautomator lookup
                child = media.child(className="android.widget.FrameLayout")
                if child.exists():
                    child_desc = child.get_desc()
                    if child_desc:
                        content_desc = child_desc
            except Exception as e:
                pass
        
        return media, content_desc"""

code = code.replace(old_get_media, new_get_media)

# Replace `_like_in_post_view` abort logic
old_like = """    def _like_in_post_view(
        self,
        mode: LikeMode,
        skip_media_check: bool = False,
        already_watched: bool = False,
    ):
        post_view_list = PostsViewList(self.device)
        opened_post_view = OpenedPostView(self.device)
        if skip_media_check:
            return
        media, content_desc = self._get_media_container()
        if content_desc is None:
            return"""

new_like = """    def _like_in_post_view(
        self,
        mode: LikeMode,
        skip_media_check: bool = False,
        already_watched: bool = False,
    ):
        post_view_list = PostsViewList(self.device)
        opened_post_view = OpenedPostView(self.device)
        if skip_media_check:
            return
            
        media, content_desc = self._get_media_container()
        
        # Avoid silent aborts if content_desc is completely unbound from IG UI v446+
        if content_desc is None:
            logger.info("Content description is fully missing. Falling back to simple click mode.")
            mode = LikeMode.SINGLE_CLICK
            already_watched = True"""

code = code.replace(old_like, new_like)

with open("InstaAddict/core/views.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Updated views.py correctly.")
