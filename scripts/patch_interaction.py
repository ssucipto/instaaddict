import re

with open('InstaAddict/core/interaction.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Add import
if 'gemini_vision' not in code:
    code = code.replace('from InstaAddict.core.utils import (', 'from InstaAddict.core.gemini_vision import get_vision_comment\nfrom InstaAddict.core.utils import (')

# Patch _comment
old_comment = """    if not session_state.check_limit(
        limit_type=session_state.Limit.COMMENTS, output=False
    ):
        if not random_choice(comment_percentage):
            return False
        universal_actions = UniversalActions(device)
        # we have to do a little swipe for preventing get the previous post comments button (which is covered by top bar, but present in hierarchy!!)
        universal_actions._swipe_points(
            direction=Direction.DOWN, delta_y=randint(150, 250)
        )"""

new_comment = """    if not session_state.check_limit(
        limit_type=session_state.Limit.COMMENTS, output=False
    ):
        if not random_choice(comment_percentage):
            return False

        # VISION AI: Take snapshot of view BEFORE opening comment box (obfuscation guard)
        logger.info("Executing Vision-AI Context Assessment...")
        smart_ai_comment = get_vision_comment(device, "current_post_target")

        universal_actions = UniversalActions(device)
        # we have to do a little swipe for preventing get the previous post comments button (which is covered by top bar, but present in hierarchy!!)
        universal_actions._swipe_points(
            direction=Direction.DOWN, delta_y=randint(150, 250)
        )"""

code = code.replace(old_comment, new_comment)

# Patch load_random_comment logic injection
old_load = """                if comment_box.exists():
                    comment = load_random_comment(my_username, media_type)
                    if comment is None:
                        UniversalActions.close_keyboard(device)
                        device.back()
                        return False
                    logger.info(
                        f"Write comment: {comment}", extra={"color": f"{Fore.CYAN}"}
                    )
                    comment_box.set_text(
                        comment, Mode.PASTE if args.dont_type else Mode.TYPE
                    )"""

new_load = """                if comment_box.exists():
                    comment = smart_ai_comment if smart_ai_comment else load_random_comment(my_username, media_type)
                    if not comment:
                        UniversalActions.close_keyboard(device)
                        device.back()
                        return False
                    
                    import time
                    # Biometric Telemetry Typing Delay Guard (150ms per character)
                    sleep_duration = len(comment) * 0.15
                    logger.info(
                        f"Write comment: {comment} (Simulating native typing delay for {sleep_duration:.2f}s)", extra={"color": f"{Fore.CYAN}"}
                    )
                    
                    comment_box.set_text(
                        comment, Mode.PASTE if args.dont_type else Mode.TYPE
                    )
                    time.sleep(sleep_duration)

                    # Ghost Typing DOM Wake-up Hack
                    # Fire physical spacebar to wake React Native event listener natively
                    try:
                        import subprocess
                        subprocess.run(f"adb -s {device.deviceV2.serial} shell input keyevent 62", shell=True)
                    except:
                        pass
"""

code = code.replace(old_load, new_load)

# Action Blocked Rescue (Plan B)
old_post = """                    if post_button.exists():
                        post_button.click()
                    else:"""

new_post = """                    if post_button.exists():
                        post_button.click()
                        time.sleep(2)
                        
                        # Graceful Degradation: Soft-Ban Action Blocked Sniffer
                        blocked = device.find(textMatches="(?i)Blocked|(?i)Restricted|(?i)Try Again Later")
                        if blocked.exists(timeout=2):
                            logger.error("Ig Action Blocked overlay detected! Disabling comments globally for this run.")
                            session_state.Limits.COMMENTS = 0 # Force soft fallback limit mapping
                            ok_btn = device.find(textMatches="(?i)Tell us|(?i)OK")
                            if ok_btn.exists(): ok_btn.click()
                    else:"""

code = code.replace(old_post, new_post)

with open('InstaAddict/core/interaction.py', 'w', encoding='utf-8') as f:
    f.write(code)
