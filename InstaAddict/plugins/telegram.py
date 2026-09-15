import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
import yaml
from colorama import Fore, Style

from InstaAddict.core.plugin_loader import Plugin

logger = logging.getLogger(__name__)


def _load_telegram_state(username: str) -> dict:
    state_file = f"accounts/{username}/telegram_state.json"
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception as e:
            logger.debug(f"Failed to load telegram state: {e}")
    return {}


def _save_telegram_state(username: str, state: dict):
    state_file = f"accounts/{username}/telegram_state.json"
    os.makedirs(f"accounts/{username}", exist_ok=True)
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.debug(f"Failed to save telegram state: {e}")


def _get_pending_media(pending_dir: str) -> List[str]:
    """Returns sorted list of pending media files by modification time (oldest to newest)."""
    if not os.path.exists(pending_dir):
        return []
    files = [
        f for f in os.listdir(pending_dir)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".mp4"))
    ]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(pending_dir, f)))
    return files


def telegram_bot_get_updates(
    bot_api_token: str, offset: Optional[int] = None, timeout: int = 5
) -> list:
    """Fetch updates from Telegram Bot API with long-polling timeout."""
    try:
        url = f"https://api.telegram.org/bot{bot_api_token}/getUpdates"
        params: Dict[str, Any] = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        res = requests.get(url, params=params, timeout=timeout + 5)
        if res.status_code == 200:
            data = res.json()
            if data.get("ok"):
                return data.get("result", [])
    except Exception as e:
        logger.debug(f"telegram_bot_get_updates error: {e}")
    return []


def telegram_bot_get_file_path(
    bot_api_token: str, file_id: str
) -> Optional[str]:
    """Retrieve relative file_path on Telegram servers for downloading."""
    try:
        url = f"https://api.telegram.org/bot{bot_api_token}/getFile"
        res = requests.get(url, params={"file_id": file_id}, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get("ok"):
                return data["result"].get("file_path")
    except Exception as e:
        logger.debug(f"telegram_bot_get_file_path error: {e}")
    return None


def telegram_bot_download_file(
    bot_api_token: str, file_path: str, dest_path: str
) -> bool:
    """Stream download a media file from Telegram to local disk."""
    try:
        url = f"https://api.telegram.org/file/bot{bot_api_token}/{file_path}"
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return True
    except Exception as e:
        logger.error(f"Failed to download media file from Telegram: {e}")
        return False


def check_telegram_inbox(
    username: str,
    telegram_config: Optional[dict] = None,
    queue_dir: Optional[str] = None,
    session_state: Optional[Any] = None,
) -> int:
    """
    Polls authorized Telegram chat for incoming media and control commands.
    Saves incoming photos with .txt sidecar captions directly into content_queue/pending.
    Returns the count of new media items queued in this run.
    """
    if not username:
        return 0

    if telegram_config is None:
        telegram_config = load_telegram_config(username)
    if not telegram_config:
        return 0

    token = telegram_config.get("telegram-api-token")
    auth_chat_id = str(telegram_config.get("telegram-chat-id", "")).strip()
    if not token or not auth_chat_id:
        return 0

    # Resolve pending queue directory
    if not queue_dir:
        queue_dir = os.path.join("accounts", username, "content_queue")
    pending_dir = os.path.join(queue_dir, "pending")
    os.makedirs(pending_dir, exist_ok=True)

    state = _load_telegram_state(username)
    last_update_id = state.get("last_update_id")
    offset = (last_update_id + 1) if last_update_id is not None else None

    updates = telegram_bot_get_updates(token, offset=offset, timeout=2)
    if not updates:
        return 0

    queued_count = 0

    for update in updates:
        update_id = update.get("update_id")
        if update_id is not None:
            state["last_update_id"] = update_id

        msg = update.get("message") or update.get("channel_post")
        if not msg:
            continue

        chat_id = str(msg.get("chat", {}).get("id", "")).strip()
        if chat_id != auth_chat_id:
            logger.warning(
                f"Ignoring Telegram message from unauthorized chat ID: {chat_id} (authorized: {auth_chat_id})"
            )
            continue

        text = (msg.get("text") or "").strip()

        # Handle Commands
        if text.startswith("/"):
            parts = text.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""

            if cmd in ["/start", "/help"]:
                help_msg = (
                    "🤖 *InstaAddict Telegram Assistant*\n\n"
                    "📸 *To Queue a Post*:\n"
                    "Send any photo or video with a caption! It will be added to your upload queue and published on schedule.\n\n"
                    "💬 *Companion Comments*:\n"
                    "Sent a photo without a caption? Just reply or send your notes in a follow-up text message—it will attach automatically!\n\n"
                    "📋 *Commands*:\n"
                    "• `/queue` - View items currently waiting in upload queue\n"
                    "• `/status` - Check live bot session status\n"
                    "• `/caption <text>` - Update caption for the latest queued post\n"
                    "• `/elaborate` - Generate AI caption & hashtags for latest post\n"
                    "• `/help` - Show this guidance"
                )
                telegram_bot_send_text(token, auth_chat_id, help_msg)
                continue

            elif cmd == "/queue":
                pending_files = []
                if os.path.exists(pending_dir):
                    pending_files = [
                        f
                        for f in sorted(os.listdir(pending_dir))
                        if f.lower().endswith(
                            (".jpg", ".jpeg", ".png", ".mp4")
                        )
                    ]
                if not pending_files:
                    queue_msg = (
                        "📂 *Upload queue is currently empty.*\n"
                        "Send me a photo with a caption to queue your next post!"
                    )
                else:
                    lines = [
                        f"📂 *Pending Upload Queue* ({len(pending_files)} item{'s' if len(pending_files) > 1 else ''}):"
                    ]
                    for idx, pf in enumerate(pending_files[:10], start=1):
                        base = os.path.splitext(pf)[0]
                        txt_file = os.path.join(pending_dir, f"{base}.txt")
                        caption_snippet = ""
                        if os.path.exists(txt_file):
                            try:
                                with open(
                                    txt_file, "r", encoding="utf-8"
                                ) as tf:
                                    caption_snippet = tf.read().strip()[:45]
                            except Exception:
                                pass
                        caption_display = (
                            f' - "{caption_snippet}..."'
                            if caption_snippet
                            else ""
                        )
                        lines.append(f"{idx}. `{pf}`{caption_display}")
                    if len(pending_files) > 10:
                        lines.append(f"... and {len(pending_files) - 10} more.")
                    queue_msg = "\n".join(lines)
                telegram_bot_send_text(token, auth_chat_id, queue_msg)
                continue

            elif cmd == "/status":
                status_lines = ["🤖 *InstaAddict Bot Status*:"]
                sessions = load_sessions(username)
                if sessions and len(sessions) > 0:
                    last_s = sessions[-1]
                    status_lines.append(
                        f"• *Last session duration*: {last_s.get('duration', 'N/A')}"
                    )
                    status_lines.append(
                        f"• *Likes last session*: {last_s.get('total_likes', 0)}"
                    )
                    status_lines.append(
                        f"• *Follows last session*: {last_s.get('total_followed', 0)}"
                    )
                pending_count = (
                    len(
                        [
                            f
                            for f in os.listdir(pending_dir)
                            if f.lower().endswith(
                                (".jpg", ".jpeg", ".png", ".mp4")
                            )
                        ]
                    )
                    if os.path.exists(pending_dir)
                    else 0
                )
                status_lines.append(f"• *Queued uploads*: {pending_count} pending")
                telegram_bot_send_text(
                    token, auth_chat_id, "\n".join(status_lines)
                )
                continue

            elif cmd == "/caption":
                if not arg:
                    telegram_bot_send_text(
                        token, auth_chat_id, "⚠️ *Usage*: `/caption <your caption text>`"
                    )
                    continue
                pending_files = _get_pending_media(pending_dir)
                if not pending_files:
                    telegram_bot_send_text(
                        token, auth_chat_id, "📂 *Upload queue is empty.* Send a photo first!"
                    )
                    continue
                target_media = pending_files[-1]
                base = os.path.splitext(target_media)[0]
                dest_txt = os.path.join(pending_dir, f"{base}.txt")
                try:
                    with open(dest_txt, "w", encoding="utf-8") as cf:
                        cf.write(arg)
                    preview = (arg[:60] + "...") if len(arg) > 60 else arg
                    telegram_bot_send_text(
                        token,
                        auth_chat_id,
                        f"✅ *Caption Updated!*\n📁 *Media*: `{target_media}`\n📝 *New Caption*: \"{preview}\"",
                    )
                except Exception as e:
                    logger.error(f"Failed to update caption: {e}")
                    telegram_bot_send_text(token, auth_chat_id, f"❌ Failed to save caption: {e}")
                continue

            elif cmd == "/elaborate":
                pending_files = _get_pending_media(pending_dir)
                if not pending_files:
                    telegram_bot_send_text(
                        token, auth_chat_id, "📂 *Upload queue is empty.* Send a photo first!"
                    )
                    continue
                target_media = pending_files[-1]
                media_path = os.path.join(pending_dir, target_media)
                base = os.path.splitext(target_media)[0]
                dest_txt = os.path.join(pending_dir, f"{base}.txt")
                current_notes = ""
                if os.path.exists(dest_txt):
                    try:
                        with open(dest_txt, "r", encoding="utf-8") as f:
                            current_notes = f.read().strip()
                    except Exception:
                        pass
                
                telegram_bot_send_text(
                    token, auth_chat_id, f"✨ *Engaging Gemini Vision AI* to elaborate caption for `{target_media}`..."
                )
                try:
                    from InstaAddict.core.gemini_vision import get_vision_caption
                    persona = "casual Instagram user"
                    acct_conf = f"accounts/{username}/config.yml"
                    if os.path.exists(acct_conf):
                        try:
                            with open(acct_conf, "r", encoding="utf-8") as yc:
                                uconf = yaml.safe_load(yc) or {}
                                persona = uconf.get("ai-persona", persona)
                        except Exception:
                            pass

                    enhanced = get_vision_caption(media_path, persona, user_context=current_notes)
                    if enhanced:
                        # Mandatorily enrich proper rotating hashtags
                        try:
                            from InstaAddict.plugins.upload_posts import UploadPostsPlugin
                            uploader = UploadPostsPlugin()
                            enhanced = uploader._enrich_hashtags_if_needed(enhanced, username)
                        except Exception:
                            pass

                        with open(dest_txt, "w", encoding="utf-8") as f:
                            f.write(enhanced)
                        telegram_bot_send_text(
                            token,
                            auth_chat_id,
                            f"✨ *AI Caption & Hashtags Generated!*\n📁 *Media*: `{target_media}`\n\n📝 *Caption*:\n\"{enhanced}\"\n\n🕒 Saved to upload queue.",
                        )
                    else:
                        telegram_bot_send_text(
                            token, auth_chat_id, "⚠️ Vision AI returned empty caption. Kept original notes."
                        )
                except Exception as e:
                    telegram_bot_send_text(token, auth_chat_id, f"❌ AI Elaboration error: {e}")
                continue

        elif text:
            # Non-command text message: attach as companion comment to latest pending media
            pending_files = _get_pending_media(pending_dir)
            if not pending_files:
                telegram_bot_send_text(
                    token,
                    auth_chat_id,
                    "ℹ️ No media is currently waiting in the upload queue.\n"
                    "Send a photo or video first, then send your companion comment/notes!",
                )
                continue

            target_media = pending_files[-1]
            base = os.path.splitext(target_media)[0]
            dest_txt = os.path.join(pending_dir, f"{base}.txt")
            try:
                with open(dest_txt, "w", encoding="utf-8") as cf:
                    cf.write(text)
                preview = (text[:60] + "...") if len(text) > 60 else text
                telegram_bot_send_text(
                    token,
                    auth_chat_id,
                    f"📝 *Companion Comment Attached!*\n"
                    f"📁 *Media*: `{target_media}`\n"
                    f"💬 *Notes*: \"{preview}\"\n\n"
                    "✨ These notes will guide Gemini Vision AI to craft the final caption and hashtags.",
                )
            except Exception as e:
                logger.error(f"Failed to attach companion comment: {e}")
            continue

        # Handle Media Attachments (Photo or Document)
        photo_list = msg.get("photo")
        doc = msg.get("document")

        file_id = None
        ext = ".jpg"

        if photo_list and isinstance(photo_list, list):
            file_id = photo_list[-1].get("file_id")
            ext = ".jpg"
        elif doc and isinstance(doc, dict):
            mime = doc.get("mime_type", "")
            file_name = doc.get("file_name", "")
            if (
                mime.startswith("image/")
                or mime.startswith("video/")
                or file_name.lower().endswith(
                    (".jpg", ".jpeg", ".png", ".mp4")
                )
            ):
                file_id = doc.get("file_id")
                ext = os.path.splitext(file_name)[1].lower() or ".jpg"

        if file_id:
            file_path = telegram_bot_get_file_path(token, file_id)
            if file_path:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                short_id = file_id[-6:] if len(file_id) >= 6 else file_id
                base_name = f"{ts}_{short_id}"
                dest_media_path = os.path.join(pending_dir, f"{base_name}{ext}")

                if telegram_bot_download_file(token, file_path, dest_media_path):
                    queued_count += 1
                    caption = (msg.get("caption") or "").strip()
                    if caption:
                        dest_txt_path = os.path.join(
                            pending_dir, f"{base_name}.txt"
                        )
                        try:
                            with open(dest_txt_path, "w", encoding="utf-8") as cf:
                                cf.write(caption)
                        except Exception as e:
                            logger.error(
                                f"Failed to write caption sidecar: {e}"
                            )

                    all_pending = [
                        f
                        for f in os.listdir(pending_dir)
                        if f.lower().endswith(
                            (".jpg", ".jpeg", ".png", ".mp4")
                        )
                    ]
                    position = len(all_pending)

                    caption_preview = (
                        (caption[:50] + "...")
                        if len(caption) > 50
                        else caption
                    )
                    caption_msg = (
                        f'\n📝 *Caption*: "{caption_preview}"'
                        if caption_preview
                        else "\n📝 *Caption*: (None provided - Vision AI will generate one if enabled)"
                    )

                    receipt = (
                        "✅ *Media Queued for Upload!*\n"
                        f"📁 *File*: `{os.path.basename(dest_media_path)}`\n"
                        f"📊 *Queue Position*: #{position}"
                        f"{caption_msg}\n\n"
                        "🕒 Will be posted automatically during your next scheduled upload cycle."
                    )
                    telegram_bot_send_text(token, auth_chat_id, receipt)
                    logger.info(
                        f"TelegramInbox: Queued new media {os.path.basename(dest_media_path)} from Telegram chat {chat_id}"
                    )

    _save_telegram_state(username, state)
    return queued_count


def load_sessions(username) -> Optional[dict]:
    try:
        with open(f"accounts/{username}/sessions.json") as json_data:
            return json.load(json_data)
    except FileNotFoundError:
        logger.error("No session data found. Skipping report generation.")
        return None


def load_telegram_config(username) -> Optional[dict]:
    try:
        with open(
            f"accounts/{username}/telegram.yml", "r", encoding="utf-8"
        ) as stream:
            return yaml.safe_load(stream)
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        return None


def telegram_bot_send_text(bot_api_token, bot_chat_ID, text):
    try:
        method = "sendMessage"
        parse_mode = "markdown"
        params = {"text": text, "chat_id": bot_chat_ID, "parse_mode": parse_mode}
        url = f"https://api.telegram.org/bot{bot_api_token}/{method}"
        return requests.get(url, params=params).json()
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return None


def telegram_notify_upload_success(
    username: str,
    media_file: str,
    caption: str = "",
    telegram_config: Optional[dict] = None,
) -> bool:
    """Sends a notification to Telegram when a post is successfully published to Instagram."""
    if not username:
        return False
    if telegram_config is None:
        telegram_config = load_telegram_config(username)
    if not telegram_config:
        return False

    token = telegram_config.get("telegram-api-token")
    chat_id = str(telegram_config.get("telegram-chat-id", "")).strip()
    if not token or not chat_id:
        return False

    cap_snippet = (caption[:60] + "...") if len(caption) > 60 else caption
    safe_cap = cap_snippet or "(No caption)"
    for ch in ["_", "*", "`", "[", "]"]:
        safe_cap = safe_cap.replace(ch, f"\\{ch}")
    safe_user = username.replace("_", "\\_")
    safe_media = media_file.replace("`", "")
    tg_msg = (
        "🚀 *Instagram Post Published!*\n\n"
        f"📷 *Media*: `{safe_media}`\n"
        f"📝 *Caption*: {safe_cap}\n\n"
        f"👤 *Account*: @{safe_user}"
    )
    res = telegram_bot_send_text(token, chat_id, tg_msg)
    return res is not None


def telegram_bot_send_photo(bot_api_token, bot_chat_id, photo_path, caption=None):
    try:
        method = "sendPhoto"
        url = f"https://api.telegram.org/bot{bot_api_token}/{method}"
        with open(photo_path, "rb") as photo_file:
            files = {"photo": photo_file}
            data = {"chat_id": bot_chat_id}
            if caption:
                data["caption"] = caption
            return requests.post(url, data=data, files=files).json()
    except Exception as e:
        logger.error(f"Error sending Telegram photo: {e}")
        return None


def _initialize_aggregated_data():
    return {
        "total_likes": 0,
        "total_watched": 0,
        "total_followed": 0,
        "total_unfollowed": 0,
        "total_comments": 0,
        "total_pm": 0,
        "duration": 0,
        "followers": float("inf"),
        "following": float("inf"),
        "followers_gained": 0,
    }


def _calculate_session_duration(session):
    try:
        start_datetime = datetime.strptime(
            session["start_time"], "%Y-%m-%d %H:%M:%S.%f"
        )
        finish_datetime = datetime.strptime(
            session["finish_time"], "%Y-%m-%d %H:%M:%S.%f"
        )
        return int((finish_datetime - start_datetime).total_seconds() / 60)
    except ValueError:
        logger.debug(
            f"{session['id']} has no finish_time. Skipping duration calculation."
        )
        return 0


def daily_summary(sessions):
    daily_aggregated_data = {}
    for session in sessions:
        date = session["start_time"][:10]
        daily_aggregated_data.setdefault(date, _initialize_aggregated_data())
        duration = _calculate_session_duration(session)
        daily_aggregated_data[date]["duration"] += duration

        for key in [
            "total_likes",
            "total_watched",
            "total_followed",
            "total_unfollowed",
            "total_comments",
            "total_pm",
        ]:
            daily_aggregated_data[date][key] += session.get(key, 0)

        followers_val = session.get("profile", {}).get("followers") or float("inf")
        following_val = session.get("profile", {}).get("following") or float("inf")
        daily_aggregated_data[date]["followers"] = min(
            followers_val,
            daily_aggregated_data[date]["followers"],
        )
        daily_aggregated_data[date]["following"] = min(
            following_val,
            daily_aggregated_data[date]["following"],
        )
    return _calculate_followers_gained(daily_aggregated_data)


def _calculate_followers_gained(aggregated_data):
    dates_sorted = sorted(aggregated_data.keys())
    previous_followers = None
    for date in dates_sorted:
        current_followers = aggregated_data[date]["followers"]
        if previous_followers is not None:
            followers_gained = current_followers - previous_followers
            aggregated_data[date]["followers_gained"] = followers_gained
        previous_followers = current_followers
    return aggregated_data


def generate_report(
    username,
    last_session,
    daily_aggregated_data,
    weekly_average_data,
    followers_now,
    following_now,
):
    return f"""
            *Stats for {username}*:

            *✨Overview after last activity*
            • {followers_now} followers ({followers_now - last_session.get("profile", {}).get("followers", 0):+})
            • {following_now} following ({following_now - last_session.get("profile", {}).get("following", 0):+})

            *🤖 Last session actions*
            • {last_session["duration"]} minutes of botting
            • {last_session["total_likes"]} likes
            • {last_session["total_followed"]} follows
            • {last_session["total_unfollowed"]} unfollows
            • {last_session["total_watched"]} stories watched
            • {last_session["total_comments"]} comments done
            • {last_session["total_pm"]} PM sent

            *📅 Today's total actions*
            • {daily_aggregated_data["duration"]} minutes of botting
            • {daily_aggregated_data["total_likes"]} likes
            • {daily_aggregated_data["total_followed"]} follows
            • {daily_aggregated_data["total_unfollowed"]} unfollows
            • {daily_aggregated_data["total_watched"]} stories watched
            • {daily_aggregated_data["total_comments"]} comments done
            • {daily_aggregated_data["total_pm"]} PM sent

            *📈 Trends*
            • {daily_aggregated_data["followers_gained"]} new followers today
            • {weekly_average_data["followers_gained"]} new followers this week

            *🗓 7-Day Average*
            • {weekly_average_data["duration"] / 7:.0f} minutes of botting
            • {weekly_average_data["total_likes"] / 7:.0f} likes
            • {weekly_average_data["total_followed"] / 7:.0f} follows
            • {weekly_average_data["total_unfollowed"] / 7:.0f} unfollows
            • {weekly_average_data["total_watched"] / 7:.0f} stories watched
            • {weekly_average_data["total_comments"] / 7:.0f} comments done
            • {weekly_average_data["total_pm"] / 7:.0f} PM sent
        """


def weekly_average(daily_aggregated_data, today) -> dict:
    weekly_average_data = _initialize_aggregated_data()

    for date in daily_aggregated_data:
        if (today - datetime.strptime(date, "%Y-%m-%d")).days > 7:
            continue
        for key in [
            "total_likes",
            "total_watched",
            "total_followed",
            "total_unfollowed",
            "total_comments",
            "total_pm",
            "duration",
            "followers_gained",
        ]:
            weekly_average_data[key] += daily_aggregated_data[date][key]
    return weekly_average_data


class TelegramReports(Plugin):
    """Generate reports at the end of the session and send them using telegram"""

    def __init__(self):
        super().__init__()
        self.description = "Generate reports at the end of the session and send them using telegram. You have to configure 'telegram.yml' in your account folder"
        self.arguments = [
            {
                "arg": "--telegram-reports",
                "help": "at the end of every session send a report to your telegram account",
                "action": "store_true",
                "operation": True,
            },
            {
                "arg": "--telegram-inbox",
                "help": "poll Telegram for incoming media and descriptions to queue for upload",
                "action": "store_true",
                "operation": True,
            },
        ]

    def run(self, config, plugin, followers_now, following_now, time_left):
        username = config.args.username
        if username is None:
            logger.error("You have to specify a username for getting reports!")
            return

        telegram_config = load_telegram_config(username)
        if not telegram_config:
            logger.error(
                f"No telegram configuration found for {username}. Skipping report generation."
            )
            return

        if getattr(config.args, "telegram_inbox", False):
            check_telegram_inbox(username, telegram_config)

        if not getattr(config.args, "telegram_reports", False):
            return

        sessions = load_sessions(username)
        if not sessions:
            logger.error(
                f"No session data found for {username}. Skipping report generation."
            )
            return

        last_session = sessions[-1]
        last_session["duration"] = _calculate_session_duration(last_session)

        daily_aggregated_data = daily_summary(sessions)
        today_data = daily_aggregated_data.get(last_session["start_time"][:10], {})
        today = datetime.now()
        weekly_average_data = weekly_average(daily_aggregated_data, today)
        report = generate_report(
            username,
            last_session,
            today_data,
            weekly_average_data,
            followers_now,
            following_now,
        )
        response = telegram_bot_send_text(
            telegram_config.get("telegram-api-token"),
            telegram_config.get("telegram-chat-id"),
            report,
        )
        if response and response.get("ok"):
            logger.info(
                "Telegram message sent successfully.",
                extra={"color": f"{Style.BRIGHT}{Fore.BLUE}"},
            )
        else:
            error = response.get("description") if response else "Unknown error"
            logger.error(f"Failed to send Telegram message: {error}")
