import uiautomator2 as u2
import time

try:
    d = u2.connect()
    print("Starting swipes...")
    w, h = d.window_size()
    sx, sy = w / 2, h * 0.8
    ex, ey = w / 2, h * 0.2

    print("Test 1: u2.swipe")
    time.sleep(2)
    d.swipe(sx, sy, ex, ey, 0.05)

    print("Test 2: u2.swipe_ext")
    time.sleep(2)
    d.swipe_ext("up", scale=0.8)

    print("Test 3: u2 shell input swipe")
    time.sleep(2)
    d.shell(f"input swipe {int(sx)} {int(sy)} {int(ex)} {int(ey)} 150")

    print("Done")
except Exception as e:
    print("Error:", e)
