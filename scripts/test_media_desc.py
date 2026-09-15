import uiautomator2 as u2

d = u2.connect("emulator-5554")
media_group = d(resourceId="com.instagram.android:id/media_group")
print("media_group exists:", media_group.exists)
if media_group.exists:
    print("media_group info:", media_group.info)
    print("media_group contentDescription:", media_group.info.get("contentDescription"))

photo_view = d(resourceId="com.instagram.android:id/row_feed_photo_imageview")
print("row_feed_photo_imageview exists:", photo_view.exists)
if photo_view.exists:
    print("row_feed_photo_imageview info:", photo_view.info)
    print("row_feed_photo_imageview contentDescription:", photo_view.info.get("contentDescription"))
