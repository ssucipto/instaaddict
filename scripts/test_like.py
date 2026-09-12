import uiautomator2 as u2

d = u2.connect("emulator-5554")
btn = d(resourceId="com.instagram.android:id/row_feed_button_like")
if btn.exists:
    print("Before click:", btn.info)
    # Check if parent or button click works
    btn.click()
    import time
    time.sleep(1)
    print("After click:", btn.info)
else:
    print("Button does not exist on current screen")
