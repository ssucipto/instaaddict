#!/usr/bin/env python3
"""
Diagnostic utility to test and verify Telegram integration for InstaAddict.
Usage:
    python scripts/check_telegram.py --username <your_account>
"""

import argparse
import os
import sys
import yaml
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

def check_telegram(username: str):
    config_path = f"accounts/{username}/telegram.yml"
    print(f"\n==================================================")
    print(f"🔍 Checking Telegram Configuration for: {username}")
    print(f"📁 Config file: {config_path}")
    print(f"==================================================")

    if not os.path.exists(config_path):
        print(f"\n❌ Configuration file NOT found at: {config_path}")
        print("👉 Create this file with the following contents:")
        print("   telegram-api-token: \"YOUR_BOT_API_TOKEN\"")
        print("   telegram-chat-id: \"YOUR_CHAT_ID\"\n")
        return False

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"❌ Failed to parse {config_path}: {e}")
        return False

    token = config.get("telegram-api-token")
    chat_id = str(config.get("telegram-chat-id", "")).strip()

    print(f"🔑 API Token: {token[:8]}...{token[-4:] if token and len(token) > 12 else ''}" if token else "🔑 API Token: (NOT SET)")
    print(f"💬 Chat ID:   {chat_id}" if chat_id else "💬 Chat ID:   (NOT SET)")

    if not token or "your-api-token" in str(token).lower() or token == "YOUR_BOT_API_TOKEN":
        print("\n⚠️  Please replace the placeholder token with your actual Telegram Bot Token from @BotFather.")
        return False

    if not chat_id or "your-chat-id" in str(chat_id).lower() or chat_id == "YOUR_CHAT_ID":
        print("\n⚠️  Please replace the placeholder chat ID with your numeric Telegram Chat ID from @myidbot.")
        return False

    # 1. Test getMe
    print("\n1️⃣  Verifying Bot Token via Telegram API (getMe)...")
    try:
        me_res = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10).json()
        if not me_res.get("ok"):
            print(f"❌ Telegram API Error: {me_res.get('description')}")
            print("👉 Check that your bot token from @BotFather is copied accurately.")
            return False
        bot_info = me_res.get("result", {})
        print(f"   ✅ Bot Authenticated: @{bot_info.get('username')} ({bot_info.get('first_name')})")
    except Exception as e:
        print(f"❌ Connection error testing bot token: {e}")
        return False

    # 2. Test sendMessage
    print(f"\n2️⃣  Sending test verification message to Chat ID: {chat_id}...")
    test_msg = (
        "🤖 *InstaAddict Telegram Integration Verified!*\n\n"
        f"✅ Bot: @{bot_info.get('username')}\n"
        f"👤 Account: `{username}`\n\n"
        "✨ *Features Ready:*\n"
        "• 📷 Send photos/videos to queue them for upload\n"
        "• 🚀 `/post` - Upload next queued post now (respects 12h cooldown)\n"
        "• ⚡ `/post_force` - Force immediate upload (bypasses cooldown)\n"
        "• 👀 `/preview` - Inspect next post photo and caption\n"
        "• 🔮 `/elaborate` - Generate AI captions & hashtags via Gemini Vision\n"
        "• 📊 `/status` or `/queue` - Inspect uploads & Android emulator\n"
        "• 🕒 `/cooldown` - Check posting rate-limit window"
    )
    try:
        send_res = requests.get(
            f"https://api.telegram.org/bot{token}/sendMessage",
            params={"chat_id": chat_id, "text": test_msg, "parse_mode": "markdown"},
            timeout=10,
        ).json()
        if not send_res.get("ok"):
            print(f"❌ Failed to send message: {send_res.get('description')}")
            print("👉 IMPORTANT: Have you opened your bot in Telegram and clicked 'START'? Bot cannot message you first until you start the chat.")
            return False
        print("   ✅ Test message delivered successfully! Check your Telegram app.")
    except Exception as e:
        print(f"❌ Error sending test message: {e}")
        return False

    # 3. Test getUpdates (Inbox Polling)
    print("\n3️⃣  Testing Inbox Polling (getUpdates)...")
    try:
        upd_res = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={"offset": -1, "timeout": 2},
            timeout=10,
        ).json()
        if upd_res.get("ok"):
            updates_count = len(upd_res.get("result", []))
            print(f"   ✅ Polling connection OK (retrieved {updates_count} recent update(s))")
        else:
            print(f"   ⚠️ Polling response: {upd_res.get('description')}")
    except Exception as e:
        print(f"   ⚠️ Polling warning: {e}")

    print("\n==================================================")
    print("🎉 Telegram integration is fully operational!")
    print("==================================================\n")
    return True


def listen_inbox(username: str):
    import time
    from InstaAddict.plugins.telegram import check_telegram_inbox, load_telegram_config
    
    config = load_telegram_config(username)
    if not config:
        print(f"❌ Configuration not found for {username}")
        return
    
    print(f"\n📡 Starting Telegram Inbox Listener for @{username}...")
    print("📲 You can now open Telegram and send:")
    print("   • A photo or video (queues for Instagram upload)")
    print("   • A companion note (attaches context to the photo)")
    print("   • /post (upload next queued post now)")
    print("   • /post_force or /post now (bypass cooldown and upload immediately)")
    print("   • /preview (view next queued post photo & caption)")
    print("   • /cooldown (check remaining time before next post)")
    print("   • /elaborate (triggers Gemini Vision AI to generate caption + hashtags)")
    print("   • /status or /queue (view pending queue & device status)")
    print("   • /help (see all commands)")
    print("\nPress Ctrl+C to exit.\n" + "-" * 50)

    try:
        while True:
            queued = check_telegram_inbox(username, telegram_config=config)
            if queued > 0:
                print(f"📥 [RECEIVED] {queued} new media item(s) downloaded and queued!")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n🛑 Stopped Telegram listener.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify Telegram integration for an InstaAddict account")
    parser.add_argument("--username", default=None, help="Target Instagram account username (defaults to the single configured account in accounts/)")
    parser.add_argument("--listen", action="store_true", help="Run live polling loop to listen for incoming Telegram messages/photos")
    args = parser.parse_args()

    target_user = args.username
    if not target_user:
        accounts_dir = "accounts"
        if os.path.exists(accounts_dir) and os.path.isdir(accounts_dir):
            cands = [
                d
                for d in os.listdir(accounts_dir)
                if os.path.isdir(os.path.join(accounts_dir, d))
                and not d.startswith(".")
            ]
            if len(cands) == 1:
                target_user = cands[0]

    if not target_user:
        print("❌ Error: --username argument is required (no single account directory found in accounts/).")
        print("Usage: python scripts/check_telegram.py --username <your_username>")
        sys.exit(1)

    if args.listen:
        listen_inbox(target_user)
    else:
        success = check_telegram(target_user)
        sys.exit(0 if success else 1)
