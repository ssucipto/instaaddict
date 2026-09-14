import os
import re
import json
import logging
import subprocess
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from InstaAddict.core.plugin_loader import Plugin
from InstaAddict.core.utils import random_sleep
from InstaAddict.core.gemini_vision import get_vision_caption
from InstaAddict.core.resources import ResourceID

logger = logging.getLogger(__name__)

# Constants
ALLOWED_EXTENSIONS: tuple = (".jpg", ".jpeg", ".png", ".mp4")
DEFAULT_RATE_LIMIT_HOURS: float = 12.0


class UploadPostsPlugin(Plugin):
    """Uploads curated content from local queue to Instagram feed."""

    def __init__(self) -> None:
        super().__init__()
        self.description: str = (
            "Uploads curated content from local queue to Instagram feed"
        )
        self.arguments: List[Dict[str, Any]] = [
            {
                "arg": "--upload-posts",
                "help": "Upload curated posts from accounts/<username>/content_queue/pending",
                "action": "store_true",
                "operation": True,
            },
            {
                "arg": "--upload-rate-limit-hours",
                "metavar": "12.0",
                "type": float,
                "default": None,
                "help": "Rate limit between uploads in hours (default: 12.0 in config or fallback, 0 to disable)",
            },
        ]

    def _resolve_username(self, configs: Any, sessions: Any) -> str:
        """Safely resolves the Instagram username across CLI args, sessions, and config path."""
        # Priority 1: CLI args
        if hasattr(configs, "args") and hasattr(configs.args, "username"):
            cli_user = configs.args.username
            if cli_user and str(cli_user).strip():
                return str(cli_user).strip()

        # Priority 2: Active session
        if sessions and len(sessions) > 0:
            session = sessions[-1]
            session_user = getattr(session, "my_username", None)
            if session_user and str(session_user).strip():
                return str(session_user).strip()

        # Priority 3: Config file path parsing
        config_path = ""
        if hasattr(configs, "args") and hasattr(configs.args, "config"):
            config_path = str(configs.args.config)

        if config_path:
            norm_path = os.path.normpath(config_path)
            parts = norm_path.split(os.sep)
            if "accounts" in parts:
                idx = parts.index("accounts")
                if idx + 1 < len(parts):
                    cand = parts[idx + 1]
                    if cand and not cand.endswith((".yml", ".yaml")):
                        return cand

        # Priority 4: Look in accounts/ directory if exactly one account exists
        accounts_dir = "accounts"
        if os.path.exists(accounts_dir) and os.path.isdir(accounts_dir):
            subdirs = [
                d
                for d in os.listdir(accounts_dir)
                if os.path.isdir(os.path.join(accounts_dir, d))
                and not d.startswith(".")
            ]
            if len(subdirs) == 1:
                return subdirs[0]

        return ""

    def _get_rate_limit_hours(self, configs: Any, config_path: str) -> float:
        """Resolves effective rate limit in hours from CLI args, YAML config, or default."""
        if hasattr(configs, "args"):
            cli_hours = getattr(configs.args, "upload_rate_limit_hours", None)
            if cli_hours is not None:
                try:
                    return float(cli_hours)
                except (ValueError, TypeError):
                    pass

        if config_path and os.path.exists(config_path):
            try:
                import yaml

                with open(config_path, "r", encoding="utf-8") as f:
                    user_conf = yaml.safe_load(f) or {}
                    if "upload-rate-limit-hours" in user_conf:
                        return float(user_conf["upload-rate-limit-hours"])
            except Exception as e:
                logger.debug(
                    f"Failed to read upload-rate-limit-hours from {config_path}: {e}"
                )

        return DEFAULT_RATE_LIMIT_HOURS

    def _is_rate_limited(self, published_dir: str, rate_limit_hours: float) -> bool:
        """Enforces a global rate limit based on recent file publication timestamps."""
        if rate_limit_hours <= 0:
            logger.info("Upload rate limit is disabled (<= 0 hours specified).")
            return False

        if not os.path.exists(published_dir):
            return False

        limit_threshold: datetime = datetime.now() - timedelta(
            hours=rate_limit_hours
        )
        latest_mtime: Optional[datetime] = None

        for root, _, files in os.walk(published_dir):
            for file in files:
                if file.lower().endswith(ALLOWED_EXTENSIONS):
                    file_path: str = os.path.join(root, file)
                    try:
                        mtime: datetime = datetime.fromtimestamp(
                            os.path.getmtime(file_path)
                        )
                        if latest_mtime is None or mtime > latest_mtime:
                            latest_mtime = mtime
                    except OSError as e:
                        logger.debug(
                            f"Failed to read file timestamp for rate limit check: {e}"
                        )

        if latest_mtime and latest_mtime > limit_threshold:
            elapsed_hours = (
                datetime.now() - latest_mtime
            ).total_seconds() / 3600.0
            remaining_hours = max(0.0, rate_limit_hours - elapsed_hours)
            logger.info(
                f"Upload rate limit active. Last upload was {elapsed_hours:.1f}h ago. "
                f"Need to wait {remaining_hours:.1f}h more before next post (limit: {rate_limit_hours}h)."
            )
            return True

        return False

    def _extract_caption(
        self, pending_dir: str, media_file: str, config_path: str
    ) -> str:
        """Extracts caption from .txt sidecar, .json sidecar, or Gemini Vision AI."""
        base_name = os.path.splitext(media_file)[0]
        media_path = os.path.join(pending_dir, media_file)

        # 1. Text file sidecar (.txt)
        txt_path = os.path.join(pending_dir, f"{base_name}.txt")
        if os.path.exists(txt_path):
            try:
                with open(txt_path, "r", encoding="utf-8") as f:
                    caption = f.read().strip()
                    if caption:
                        logger.info(
                            f"Human text caption override found for {media_file} ({txt_path})."
                        )
                        return caption
            except Exception as e:
                logger.warning(
                    f"Failed reading text caption override {txt_path}: {e}"
                )

        # 2. JSON file sidecar (.json)
        json_path = os.path.join(pending_dir, f"{base_name}.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    caption = data.get("caption", "").strip()
                    if caption:
                        logger.info(
                            f"Human JSON caption override found for {media_file} ({json_path})."
                        )
                        return caption
            except Exception as e:
                logger.warning(
                    f"Failed reading JSON caption override {json_path}: {e}"
                )

        # 3. Gemini Vision AI Autopilot
        logger.info(
            f"No caption sidecar found for {media_file}. Engaging AI Autopilot Vision-Captioner..."
        )
        persona = "casual Instagram user"
        if config_path and os.path.exists(config_path):
            try:
                import yaml

                with open(config_path, "r", encoding="utf-8") as yc:
                    user_conf = yaml.safe_load(yc) or {}
                    persona = user_conf.get("ai-persona", persona)
            except Exception:
                pass

        try:
            caption = get_vision_caption(media_path, persona)
            if caption:
                return caption.strip()
        except Exception as e:
            logger.error(
                f"Gemini Vision AI caption generation failed for {media_file}: {e}"
            )

        return ""

    def run(
        self,
        device: Any,
        configs: Any,
        storage: Any,
        sessions: Any,
        profile_filter: Any,
        plugin: Any,
    ) -> None:
        """Main plugin execution hook."""
        username = self._resolve_username(configs, sessions)
        if not username:
            logger.error(
                "UploadPostsPlugin: Unable to resolve account username. Cannot locate content queue."
            )
            return

        config_path: str = ""
        if hasattr(configs, "args") and hasattr(configs.args, "config"):
            config_path = str(configs.args.config)

        # Support standard content_queue and legacy upload_queue
        pending_candidates = [
            os.path.join("accounts", username, "content_queue", "pending"),
            os.path.join("accounts", username, "upload_queue", "pending"),
        ]
        pending_dir = None
        for cand in pending_candidates:
            if os.path.exists(cand):
                pending_dir = cand
                break

        if not pending_dir:
            pending_dir = pending_candidates[0]
            logger.info(
                f"UploadPostsPlugin: Pending queue directory does not exist: {pending_dir}. Skipping upload."
            )
            return

        published_dir = os.path.join(os.path.dirname(pending_dir), "published")

        rate_limit_hours = self._get_rate_limit_hours(configs, config_path)
        if self._is_rate_limited(published_dir, rate_limit_hours):
            return

        # Case-insensitive media discovery
        all_files = sorted(os.listdir(pending_dir))
        media_files = [
            f for f in all_files if f.lower().endswith(ALLOWED_EXTENSIONS)
        ]

        if not media_files:
            logger.info(
                f"UploadPostsPlugin: No pending media files found in queue: {pending_dir}"
            )
            return

        logger.info(
            f"UploadPostsPlugin: Found {len(media_files)} queued media item(s) in {pending_dir}."
        )

        for media_file in media_files:
            base_name = os.path.splitext(media_file)[0]
            media_path = os.path.join(pending_dir, media_file)

            caption = self._extract_caption(
                pending_dir, media_file, config_path
            )

            caption_snippet = (
                (caption[:40] + "...") if len(caption) > 40 else caption
            )
            logger.info(
                f"Uploading {media_file} with caption: {caption_snippet!r}"
            )
            success = self._upload_to_ig(device, media_path, caption)

            if success:
                logger.info(
                    f"Successfully uploaded {media_file}! Archiving media and sidecars to published directory."
                )
                os.makedirs(published_dir, exist_ok=True)

                # Move media file
                dest_media = os.path.join(published_dir, media_file)
                if os.path.exists(dest_media):
                    os.remove(dest_media)
                os.rename(media_path, dest_media)

                # Move .txt sidecar if present
                txt_path = os.path.join(pending_dir, f"{base_name}.txt")
                if os.path.exists(txt_path):
                    dest_txt = os.path.join(published_dir, f"{base_name}.txt")
                    if os.path.exists(dest_txt):
                        os.remove(dest_txt)
                    os.rename(txt_path, dest_txt)

                # Move .json sidecar if present
                json_path = os.path.join(pending_dir, f"{base_name}.json")
                if os.path.exists(json_path):
                    dest_json = os.path.join(
                        published_dir, f"{base_name}.json"
                    )
                    if os.path.exists(dest_json):
                        os.remove(dest_json)
                    os.rename(json_path, dest_json)

                if sessions and len(sessions) > 0:
                    current_session = sessions[-1]
                    if hasattr(current_session, "totalUploadsSuccess"):
                        current_session.totalUploadsSuccess += 1
                    if not hasattr(current_session, "uploadHistory") or current_session.uploadHistory is None:
                        current_session.uploadHistory = []
                    current_session.uploadHistory.append(
                        {
                            "file": media_file,
                            "status": "success",
                            "caption": caption[:100],
                            "timestamp": str(datetime.now()),
                        }
                    )
            else:
                logger.error(
                    f"Upload failed for {media_file}. Retaining in pending queue for retry."
                )
                if sessions and len(sessions) > 0:
                    current_session = sessions[-1]
                    if hasattr(current_session, "totalUploadsFailed"):
                        current_session.totalUploadsFailed += 1
                    if not hasattr(current_session, "uploadHistory") or current_session.uploadHistory is None:
                        current_session.uploadHistory = []
                    current_session.uploadHistory.append(
                        {
                            "file": media_file,
                            "status": "failed",
                            "caption": caption[:100],
                            "timestamp": str(datetime.now()),
                        }
                    )

            # Process exactly one post per plugin invocation
            break

    def _execute_adb(self, serial: str, command_args: List[str]) -> bool:
        """Secure isolated execution of ADB commands mapping native array signatures."""
        cmd: List[str] = ["adb", "-s", serial] + command_args
        try:
            subprocess.run(
                cmd,
                shell=False,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"ADB execution failed ({command_args[0]}): Code {e.returncode}")
            return False
        except FileNotFoundError:
            logger.error("ADB executable not found in system PATH.")
            return False

    def _get_mediastore_id(
        self, serial: str, filename: str, is_video: bool = False
    ) -> Optional[str]:
        """Queries Android MediaStore for the _id of a pushed media file."""
        uri = (
            "content://media/external/video/media"
            if is_video
            else "content://media/external/images/media"
        )
        cmd = [
            "adb",
            "-s",
            serial,
            "shell",
            "content",
            "query",
            "--uri",
            uri,
            "--projection",
            "_id:_data",
        ]
        try:
            res = subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=10
            )
            for line in res.stdout.splitlines():
                if filename in line:
                    m = re.search(r"_id=(\d+)", line)
                    if m:
                        return m.group(1)
        except Exception as e:
            logger.debug(f"MediaStore query error: {e}")
        return None

    def _upload_to_ig(
        self, device: Any, media_path: str, caption: str
    ) -> bool:
        """Drives Instagram composer flow using native ADD_TO_FEED intent and UIAutomator2."""
        serial: str = device.deviceV2.serial
        filename: str = os.path.basename(media_path)
        is_video: bool = filename.lower().endswith(".mp4")
        mime_type: str = (
            "video/mp4"
            if is_video
            else ("image/png" if filename.lower().endswith(".png") else "image/jpeg")
        )
        device_path: str = f"/sdcard/Pictures/{filename}"

        # 1. Push media to device storage
        logger.info(f"Pushing {filename} to device ({device_path})...")
        pushed = self._execute_adb(serial, ["push", media_path, device_path])
        if not pushed:
            logger.error(f"Failed pushing media to device storage: {device_path}")
            return False

        # 2. Trigger media scanner broadcast for indexing
        self._execute_adb(
            serial,
            [
                "shell",
                "am",
                "broadcast",
                "-a",
                "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
                "-d",
                f"file://{device_path}",
            ],
        )
        random_sleep(1, 2)

        # 3. Query MediaStore ID
        media_id = self._get_mediastore_id(serial, filename, is_video)
        if not media_id:
            # Fallback insert into MediaStore if broadcast scan did not index immediately
            uri = (
                "content://media/external/video/media"
                if is_video
                else "content://media/external/images/media"
            )
            self._execute_adb(
                serial,
                [
                    "shell",
                    "content",
                    "insert",
                    "--uri",
                    uri,
                    "--bind",
                    f"_data:s:{device_path}",
                    "--bind",
                    f"mime_type:s:{mime_type}",
                ],
            )
            random_sleep(1, 2)
            media_id = self._get_mediastore_id(serial, filename, is_video)

        if media_id:
            base_uri = (
                "content://media/external/video/media"
                if is_video
                else "content://media/external/images/media"
            )
            stream_uri = f"{base_uri}/{media_id}"
        else:
            stream_uri = f"file://{device_path}"

        logger.info(f"Target media stream URI: {stream_uri}")

        # 4. Launch Instagram ADD_TO_FEED intent
        logger.info("Launching Instagram ADD_TO_FEED intent...")
        intent_args = [
            "shell",
            "am",
            "start",
            "-a",
            "com.instagram.share.ADD_TO_FEED",
            "-t",
            mime_type,
            "--eu",
            "android.intent.extra.STREAM",
            stream_uri,
            "-n",
            "com.instagram.android/com.instagram.share.handleractivity.ShareHandlerActivity",
        ]
        launched = self._execute_adb(serial, intent_args)
        if not launched:
            logger.warning(
                "ADD_TO_FEED launch failed, attempting android.intent.action.SEND fallback..."
            )
            fallback_args = [
                "shell",
                "am",
                "start",
                "-a",
                "android.intent.action.SEND",
                "-t",
                mime_type,
                "--eu",
                "android.intent.extra.STREAM",
                stream_uri,
                "-p",
                "com.instagram.android",
            ]
            self._execute_adb(serial, fallback_args)

        random_sleep(3, 5)

        d = device.deviceV2
        app_id = getattr(device, "app_id", "com.instagram.android")
        res_attr = getattr(device, "ResourceID", None)
        if res_attr is None or isinstance(res_attr, type):
            resource_id = ResourceID(app_id)
        else:
            resource_id = res_attr

        # 5. Advance composer steps (Crop/Audio -> Filters -> Share Sheet)
        max_steps = 6
        share_sheet_reached = False
        for step in range(max_steps):
            # Check if Share Sheet is visible
            caption_input = d(resourceId=resource_id.CAPTION_INPUT_TEXT_VIEW)
            share_footer = d(resourceId=resource_id.SHARE_FOOTER_BUTTON)
            if caption_input.exists(timeout=2) or share_footer.exists(timeout=2):
                logger.info("Reached Instagram post Share Sheet.")
                share_sheet_reached = True
                break

            # Check if "Sharing posts" or OK modal is blocking
            ok_btn = d(textMatches="(?i)^OK$")
            if ok_btn.exists(timeout=2):
                logger.info("Dismissing 'Sharing posts' modal dialog...")
                ok_btn.click()
                random_sleep(1, 2)
                continue

            # Tap Next button
            next_btn = d(resourceId=resource_id.MEDIA_THUMBNAIL_TRAY_BUTTON)
            if not next_btn.exists(timeout=2):
                next_btn = d(
                    resourceId=resource_id.MEDIA_THUMBNAIL_TRAY_BUTTON_TEXT
                )
            if not next_btn.exists(timeout=2):
                next_btn = d(textMatches="(?i)^Next$")
            if not next_btn.exists(timeout=2):
                next_btn = d(descriptionMatches="(?i)^Next$")

            if next_btn.exists(timeout=3):
                logger.info(
                    f"Advancing composer step {step + 1} (tapping Next)..."
                )
                next_btn.click()
                random_sleep(2, 4)
            else:
                logger.debug(f"Step {step + 1}: Waiting for composer screen...")
                random_sleep(1, 2)

        if not share_sheet_reached:
            # Check one more time with broad locators
            if (
                d(resourceId=resource_id.CAPTION_INPUT_TEXT_VIEW).exists(
                    timeout=3
                )
                or d(resourceId=resource_id.SHARE_FOOTER_BUTTON).exists(
                    timeout=3
                )
                or d(descriptionMatches="(?i)Share").exists(timeout=3)
            ):
                share_sheet_reached = True

        if not share_sheet_reached:
            logger.error("Failed to navigate to post Share Sheet.")
            return False

        # 6. Set caption if provided
        if caption:
            caption_box = d(resourceId=resource_id.CAPTION_INPUT_TEXT_VIEW)
            if not caption_box.exists(timeout=3):
                caption_box = d(
                    classNameMatches=".*EditText.*|.*AutoCompleteTextView.*"
                )

            if caption_box.exists(timeout=5):
                logger.info(f"Setting post caption ({len(caption)} characters)...")
                caption_box.set_text(caption)
                random_sleep(1, 2)
            else:
                logger.warning(
                    "Caption input field not found on Share Sheet. Proceeding without caption."
                )

        # 7. Tap Share
        share_btn = d(resourceId=resource_id.SHARE_FOOTER_BUTTON)
        if not share_btn.exists(timeout=3):
            share_btn = d(textMatches="(?i)^Share$")
        if not share_btn.exists(timeout=2):
            share_btn = d(descriptionMatches="(?i)^Share$")

        if share_btn.exists(timeout=5):
            logger.info("Tapping Share button to publish post...")
            share_btn.click()
            logger.info(
                "Share clicked. Waiting for upload completion state..."
            )
            random_sleep(8, 12)

            # Verification: Check return to Home feed or MainTabActivity
            home_btn = d(descriptionMatches="(?i).*Home.*")
            if home_btn.exists(timeout=5):
                logger.info("Post uploaded successfully (Home feed visible).")
                return True

            try:
                cur_app = d.app_current()
                if cur_app and cur_app.get("activity") in [
                    ".activity.MainTabActivity",
                    "com.instagram.mainactivity.MainActivity",
                    "com.instagram.mainactivity.LauncherActivity",
                ]:
                    logger.info("Post uploaded successfully (Returned to MainTabActivity).")
                    return True
            except Exception:
                pass

            logger.info("Post upload completed.")
            return True
        else:
            logger.error("Cannot locate Share button on Share Sheet.")
            return False
