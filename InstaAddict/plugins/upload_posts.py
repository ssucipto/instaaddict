import os
import json
import logging
import subprocess
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
from InstaAddict.core.plugin_loader import Plugin
from InstaAddict.core.utils import random_sleep
from InstaAddict.core.gemini_vision import get_vision_caption

logger = logging.getLogger(__name__)

# Constants
ALLOWED_EXTENSIONS: tuple = ('.jpg', '.jpeg', '.png', '.mp4')
RATE_LIMIT_HOURS: int = 12

class UploadPostsPlugin(Plugin):
    """Uploads curated content from local queue to Instagram feed."""

    def __init__(self) -> None:
        super().__init__()
        self.description: str = "Uploads curated content from local queue to Instagram feed"
        self.arguments: List[Dict[str, Any]] = [
            {
                "arg": "--upload-posts",
                "help": "Upload curated posts from accounts/<username>/content_queue/pending",
                "action": "store_true",
                "operation": True,
            }
        ]

    def _is_rate_limited(self, published_dir: str) -> bool:
        """Enforces a global rate limit based on recent file publication timestamps."""
        if not os.path.exists(published_dir):
            return False
        
        limit_threshold: datetime = datetime.now() - timedelta(hours=RATE_LIMIT_HOURS)
        for root, _, files in os.walk(published_dir):
            for file in files:
                file_path: str = os.path.join(root, file)
                try:
                    mtime: datetime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if mtime > limit_threshold:
                        logger.info(f"Upload rate limit active. Waiting {RATE_LIMIT_HOURS}h+ to upload next queued post.")
                        return True
                except OSError as e:
                    logger.debug(f"Failed to read file timestamp for rate limit check: {e}")
        return False

    def run(self, device: Any, configs: Any, storage: Any, sessions: Any, profile_filter: Any, plugin: Any) -> None:
        """Main plugin execution hook."""
        # Resolve username safely
        config_path: str = str(configs.args.config)
        username: str = config_path.split('/')[-2] if '/' in config_path else config_path.split('\\')[-2]
        
        pending_dir: str = os.path.join("accounts", username, "content_queue", "pending")
        published_dir: str = os.path.join("accounts", username, "content_queue", "published")

        if self._is_rate_limited(published_dir):
            return

        if not os.path.exists(pending_dir):
            return

        # M6: Autopilot Uploads (Media-First Architecture)
        all_files = os.listdir(pending_dir)
        media_files = [f for f in all_files if f.endswith(ALLOWED_EXTENSIONS)]
        
        if not media_files:
            return

        for media_file in media_files:
            base_name = os.path.splitext(media_file)[0]
            media_path = os.path.join(pending_dir, media_file)
            json_path = os.path.join(pending_dir, f"{base_name}.json")
            
            caption = ""
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        caption = data.get("caption", "")
                        logger.info(f"Human override caption found for {media_file}.")
                except Exception as e:
                    logger.error(f"Failed reading JSON override {json_path}: {e}")
            
            if not caption:
                logger.info(f"No caption provided for {media_file}. Engaging AI Autopilot Vision-Captioner...")
                import yaml
                persona = "casual Instagram user"
                try:
                    with open(config_path, 'r') as yc:
                        user_conf = yaml.safe_load(yc)
                        persona = user_conf.get("ai-persona", persona)
                except: pass
                
                caption = get_vision_caption(media_path, persona)
            
            logger.info(f"Uploading {media_file} with AI/Human caption: {caption[:30]}...")
            success = self._upload_to_ig(device, media_path, caption)

            if success:
                logger.info(f"Successfully posted! Archiving payload.")
                os.makedirs(published_dir, exist_ok=True)
                os.rename(media_path, os.path.join(published_dir, media_file))
                if os.path.exists(json_path):
                    os.rename(json_path, os.path.join(published_dir, f"{base_name}.json"))
            else:
                logger.error(f"Upload failed for {media_file}. Queued for retry.")
            
            break

    def _execute_adb(self, serial: str, command_args: List[str]) -> bool:
        """Secure isolated execution of ADB commands mapping native array signatures."""
        cmd: List[str] = ["adb", "-s", serial] + command_args
        try:
            subprocess.run(cmd, shell=False, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"ADB execution failed. Code {e.returncode}")
            return False
        except FileNotFoundError:
            logger.error("ADB executable not found in PATH constraints.")
            return False

    def _upload_to_ig(self, device: Any, media_path: str, caption: str) -> bool:
        """Drives the UI to post a photo/video."""
        device_path: str = f"/sdcard/Pictures/{os.path.basename(media_path)}"
        
        # Secured push block without shell injection
        self._execute_adb(device.deviceV2.serial, ["push", media_path, device_path])
        self._execute_adb(device.deviceV2.serial, [
            "shell", "am", "broadcast", "-a", 
            "android.intent.action.MEDIA_SCANNER_SCAN_FILE", 
            "-d", f"file://{device_path}"
        ])
        random_sleep(2, 4)

        home_btn = device.deviceV2(descriptionMatches="(?i).*Home.*")
        if home_btn.exists():
            home_btn.click()
            random_sleep(1, 2)

        create_btn = device.deviceV2(descriptionMatches="(?i)New post.*|(?i)Camera.*|(?i)Create")
        if not create_btn.exists(timeout=5):
            tab_bar = device.deviceV2(resourceIdMatches=".*tab_bar.*").child(className="android.widget.FrameLayout", index=2)
            if tab_bar.exists():
                create_btn = tab_bar
        
        if not create_btn.exists():
            logger.error("Cannot locate Create New Post UI Hook.")
            return False

        create_btn.click()
        random_sleep(3, 5)

        next_btn = device.deviceV2(textMatches="(?i)Next|(?i)Arrow")
        if next_btn.exists(timeout=5):
            next_btn.click()
            random_sleep(2, 4)
            if next_btn.exists(timeout=3):
                next_btn.click()
        else:
            arrow = device.deviceV2(descriptionMatches="(?i)Next")
            if arrow.exists(timeout=3):
                arrow.click()
                random_sleep(2, 4)
                if arrow.exists(timeout=3):
                    arrow.click()

        random_sleep(2, 4)
        caption_box = device.deviceV2(classNameMatches=".*EditText.*")
        if caption_box.exists(timeout=5):
            caption_box.set_text(caption.replace("\n", "  "))
            random_sleep(1, 2)

        share_btn = device.deviceV2(textMatches="(?i)Share")
        if not share_btn.exists(timeout=2):
             share_btn = device.deviceV2(descriptionMatches="(?i)Share")

        if share_btn.exists(timeout=5):
            share_btn.click()
            logger.info("Share clicked. Waiting for upload completion state...")
            random_sleep(10, 15)
            
            in_feed: bool = device.deviceV2(descriptionMatches="(?i).*Home.*").exists(timeout=5)
            if in_feed:
                return True
            else:
                random_sleep(8, 10)
                return True
        else:
            return False
