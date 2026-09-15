import json
import logging
import os
import re
from datetime import datetime, timedelta
from random import sample, shuffle
from typing import Any, Dict, List, Optional, Set

import yaml
from atomicwrites import atomic_write

logger = logging.getLogger(__name__)

FILENAME_HASHTAGS_YML = "hashtags.yml"
FILENAME_DISCOVERED_HASHTAGS = "discovered_hashtags.json"

BLACKLIST_PATTERNS: Set[str] = {
    "like4like",
    "l4l",
    "f4f",
    "followforfollow",
    "follow4follow",
    "giveaway",
    "contest",
    "reels",
    "viral",
    "fyp",
    "explorepage",
    "crypto",
    "nsfw",
    "tagsforlikes",
    "instalike",
    "followme",
    "likeforlikes",
}

RELEVANCE_KEYWORDS: Set[str] = {
    "dog",
    "terrier",
    "jrt",
    "pup",
    "puppy",
    "pet",
    "perth",
    "wa",
    "beach",
    "bark",
    "tail",
    "paw",
    "fur",
    "australia",
    "aussie",
    "jackrussell",
    "canine",
    "hound",
    "mutt",
    "woof",
    "pooch",
}


class HashtagManager:
    """Manages tiered hashtag master pools, in-app caption harvesting,

    AI persona expansion, and deterministic Add/Rotate/Prune rules.
    """

    _instances: Dict[str, "HashtagManager"] = {}

    @classmethod
    def get_instance(
        cls,
        username: str,
        account_dir: Optional[str] = None,
        hashtags_file: Optional[str] = None,
    ) -> "HashtagManager":
        """Singleton accessor per account username."""
        if not username:
            username = "default"
        if username not in cls._instances:
            cls._instances[username] = cls(
                username, account_dir=account_dir, hashtags_file=hashtags_file
            )
        return cls._instances[username]

    def __init__(
        self,
        username: str,
        account_dir: Optional[str] = None,
        hashtags_file: Optional[str] = None,
    ):
        self.username = username
        self.account_dir = account_dir or os.path.join("accounts", username)
        if not os.path.exists(self.account_dir):
            os.makedirs(self.account_dir, exist_ok=True)

        self.hashtags_yml_path = hashtags_file or os.path.join(
            self.account_dir, FILENAME_HASHTAGS_YML
        )
        self.discovered_path = os.path.join(
            self.account_dir, FILENAME_DISCOVERED_HASHTAGS
        )

        self.master_data: Dict[str, Any] = self._load_master_data()
        self.discovered_tags: Dict[str, Any] = self._load_discovered_tags()
        self._dirty = False

    def _load_master_data(self) -> Dict[str, Any]:
        """Loads hashtags.yml with fallback template generation."""
        if os.path.isfile(self.hashtags_yml_path):
            try:
                with open(self.hashtags_yml_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        return data
            except Exception as e:
                logger.warning(
                    f"Failed to parse {self.hashtags_yml_path}: {e}. Creating default."
                )

        default_data: Dict[str, Any] = {
            "version": "1.0.0",
            "username": self.username,
            "enabled": True,
            "cooldown_sessions": 2,
            "min_seen_to_promote": 3,
            "tiers": {
                "tier1_local_perth": {
                    "name": "Local Community",
                    "session_sample_count": 2,
                    "tags": ["perthdogs", "dogsofperth"],
                },
                "tier2_breed_jrt": {
                    "name": "Niche & Breed",
                    "session_sample_count": 2,
                    "tags": ["jackrussell", "jrt"],
                },
                "tier3_lifestyle_adventure": {
                    "name": "Lifestyle & Activity",
                    "session_sample_count": 1,
                    "tags": ["dogbeach", "hikingwithdogs"],
                },
                "tier4_reach_and_trending": {
                    "name": "General Reach & Themes",
                    "session_sample_count": 1,
                    "tags": ["dogsofinstagram", "puppylove"],
                },
            },
            "cooldowns": {},
            "saturated_tags": {},
            "dead_tags": [],
        }
        return default_data

    def _load_discovered_tags(self) -> Dict[str, Any]:
        """Loads discovered_hashtags.json with safe recovery."""
        if os.path.isfile(self.discovered_path):
            try:
                with open(self.discovered_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception as e:
                logger.warning(
                    f"Failed to load {self.discovered_path}: {e}. Starting fresh."
                )
        return {}

    def has_tiered_sources(self) -> bool:
        """Returns True if hashtags.yml is active and contains tags in tiers."""
        if not self.master_data.get("enabled", True):
            return False
        tiers = self.master_data.get("tiers", {})
        total_tags = sum(len(t.get("tags", [])) for t in tiers.values())
        return total_tags > 0

    # ─────────────────────────────────────────────────────────────
    # Strategy 2: Caption Harvester & Add Rules
    # ─────────────────────────────────────────────────────────────

    def harvest_from_caption(
        self, caption_text: str, source_tag: Optional[str] = None
    ) -> List[str]:
        """Extracts hashtags from a post caption, updates discovery stats,

        and applies promotion rules (R-ADD-1 to R-ADD-4).
        """
        if not caption_text or not isinstance(caption_text, str):
            return []

        raw_tags = re.findall(r"#([a-zA-Z0-9_]+)", caption_text)
        if not raw_tags:
            return []

        promoted_tags: List[str] = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for tag in raw_tags:
            clean_tag = tag.strip().lower()
            if len(clean_tag) < 3 or len(clean_tag) > 35:
                continue

            # R-ADD-2: Anti-Spam Blacklist Filter
            if clean_tag in BLACKLIST_PATTERNS or any(
                bp in clean_tag for bp in BLACKLIST_PATTERNS
            ):
                continue

            # Record or update discovery metrics
            tag_entry = self.discovered_tags.get(
                clean_tag,
                {
                    "seen_count": 0,
                    "first_seen": now_str,
                    "last_seen": now_str,
                    "sources": [],
                    "promoted": False,
                },
            )
            tag_entry["seen_count"] += 1
            tag_entry["last_seen"] = now_str
            if source_tag and source_tag not in tag_entry["sources"]:
                tag_entry["sources"].append(source_tag)
            self.discovered_tags[clean_tag] = tag_entry
            self._dirty = True

            # Evaluate R-ADD-1, R-ADD-3, R-ADD-4 for Promotion
            min_seen = self.master_data.get("min_seen_to_promote", 3)
            if tag_entry["seen_count"] >= min_seen and not tag_entry.get(
                "promoted", False
            ):
                if self._is_relevant_tag(clean_tag):
                    tier_key = self._classify_tag_tier(clean_tag)
                    if self._add_tag_to_tier(tier_key, clean_tag):
                        tag_entry["promoted"] = True
                        promoted_tags.append(clean_tag)
                        logger.info(
                            f"[HashtagHarvester] Promoted #{clean_tag} to {tier_key} (seen {tag_entry['seen_count']}x)."
                        )

        self.save_all()
        return promoted_tags

    def _is_relevant_tag(self, tag: str) -> bool:
        """R-ADD-3: Semantic relevance check against target niche."""
        tag_lower = tag.lower()
        if any(keyword in tag_lower for keyword in RELEVANCE_KEYWORDS):
            return True
        return False

    def _classify_tag_tier(self, tag: str) -> str:
        """R-ADD-4: Categorizes a tag into an appropriate master tier."""
        tag_lower = tag.lower()
        if any(
            loc in tag_lower
            for loc in ["perth", "wa", "westernaustralia", "fremantle", "aus"]
        ):
            return "tier1_local_perth"
        if any(
            breed in tag_lower
            for breed in ["jack", "jrt", "terrier", "russell"]
        ):
            return "tier2_breed_jrt"
        if any(
            act in tag_lower
            for act in [
                "beach",
                "hike",
                "adventure",
                "outdoor",
                "play",
                "walk",
                "run",
            ]
        ):
            return "tier3_lifestyle_adventure"
        return "tier4_reach_and_trending"

    def _add_tag_to_tier(self, tier_key: str, tag: str) -> bool:
        """Appends tag to tier in master_data if not already present."""
        tiers = self.master_data.setdefault("tiers", {})
        if tier_key not in tiers:
            # Fallback to first tier if specific key not present
            tier_key = next(iter(tiers.keys()), "tier4_reach_and_trending")
            if tier_key not in tiers:
                tiers[tier_key] = {
                    "name": "General",
                    "session_sample_count": 1,
                    "tags": [],
                }

        tier_tags = tiers[tier_key].setdefault("tags", [])
        dead_tags = set(self.master_data.get("dead_tags", []))
        if tag not in tier_tags and tag not in dead_tags:
            tier_tags.append(tag)
            self._dirty = True
            return True
        return False

    # ─────────────────────────────────────────────────────────────
    # Rotation Engine: Balanced Tier Sampling & Anti-Fatigue
    # ─────────────────────────────────────────────────────────────

    def get_session_sources(
        self,
        fallback_sources: Optional[List[str]] = None,
        total_limit: Optional[int] = None,
        count: Optional[int] = None,
    ) -> List[str]:
        """R-ROT-1 to R-ROT-3: Samples tier-balanced, cooldown-aware hashtags."""
        if total_limit is None and count is not None:
            total_limit = count
        if not self.has_tiered_sources():
            return fallback_sources or []

        tiers = self.master_data.get("tiers", {})
        cooldowns: Dict[str, int] = self.master_data.setdefault("cooldowns", {})
        dead_tags: Set[str] = set(self.master_data.get("dead_tags", []))
        saturated_tags: Dict[str, Any] = self.master_data.setdefault(
            "saturated_tags", {}
        )
        cooldown_sessions = self.master_data.get("cooldown_sessions", 2)

        # Step 1: Decrement active cooldowns for non-active tags
        expired_cooldowns: List[str] = []
        for tag, cd in cooldowns.items():
            if cd > 1:
                cooldowns[tag] = cd - 1
            else:
                expired_cooldowns.append(tag)
        for tag in expired_cooldowns:
            del cooldowns[tag]

        # Step 2: Sample proportionally from each tier
        selected_tags: List[str] = []
        for tier_key, tier in tiers.items():
            tags = tier.get("tags", [])
            needed = tier.get("session_sample_count", 1)
            if not tags:
                continue

            # Exclude dead, currently saturated, and cooldown tags
            available = [
                t
                for t in tags
                if t not in dead_tags
                and not self._is_tag_saturated(t, saturated_tags)
                and t not in cooldowns
            ]

            # If all available are cooling down, relax cooldown for this tier
            if not available:
                available = [
                    t
                    for t in tags
                    if t not in dead_tags
                    and not self._is_tag_saturated(t, saturated_tags)
                ]

            if available:
                count_to_sample = min(needed, len(available))
                sampled = sample(available, count_to_sample)
                selected_tags.extend(sampled)
                # Set cooldown on selected tags
                for t in sampled:
                    cooldowns[t] = cooldown_sessions

        # Step 3: R-ROT-3 Shuffle execution order
        shuffle(selected_tags)

        if total_limit and total_limit > 0:
            selected_tags = selected_tags[:total_limit]

        self._dirty = True
        self.save_all()
        return selected_tags if selected_tags else (fallback_sources or [])

    def get_post_hashtags(self, count: int = 5) -> List[str]:
        """Returns balanced rotating hashtags for newly uploaded posts across active tiers."""
        tags = self.get_session_sources(total_limit=count)
        if not tags:
            for tier in self.master_data.get("tiers", {}).values():
                for t in tier.get("tags", []):
                    if t not in tags:
                        tags.append(t)
                        if len(tags) >= count:
                            break
                if len(tags) >= count:
                    break
        return tags[:count]

    def _is_tag_saturated(self, tag: str, saturated_tags: Dict[str, Any]) -> bool:
        """Checks if a tag is benched for saturation."""
        if tag not in saturated_tags:
            return False
        sat_val = saturated_tags[tag]
        if isinstance(sat_val, str):
            try:
                exp = datetime.strptime(sat_val, "%Y-%m-%d %H:%M:%S")
                if datetime.now() < exp:
                    return True
                else:
                    # Saturation expired
                    del saturated_tags[tag]
                    return False
            except Exception:
                return False
        return False

    # ─────────────────────────────────────────────────────────────
    # Pruning Engine: Dead Tag & Saturation Benching
    # ─────────────────────────────────────────────────────────────

    def record_hashtag_result(
        self,
        tag: str,
        posts_found: bool = True,
        already_liked_exhausted: bool = False,
    ) -> None:
        """R-PRN-1 & R-PRN-2: Records search/interaction outcomes to prune dead or saturated tags."""
        if not tag:
            return
        clean_tag = tag.lstrip("#").lower()

        # R-PRN-1: Dead Tag Pruning
        if not posts_found:
            dead_tags = self.master_data.setdefault("dead_tags", [])
            if clean_tag not in dead_tags:
                dead_tags.append(clean_tag)
                # Remove from tier active lists
                for tier in self.master_data.get("tiers", {}).values():
                    tags = tier.get("tags", [])
                    if clean_tag in tags:
                        tags.remove(clean_tag)
                logger.warning(
                    f"[HashtagManager] Tag #{clean_tag} produced 0 results. Marked as DEAD and pruned."
                )
                self._dirty = True

        # R-PRN-2: Saturation Benching
        elif already_liked_exhausted:
            saturated = self.master_data.setdefault("saturated_tags", {})
            current_count = saturated.get(clean_tag, 0)
            if isinstance(current_count, int):
                new_count = current_count + 1
                if new_count >= 2:
                    # Bench for 7 days
                    bench_until = datetime.now() + timedelta(days=7)
                    saturated[clean_tag] = bench_until.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    logger.info(
                        f"[HashtagManager] Tag #{clean_tag} hit already-liked limit repeatedly. Benched for 7 days."
                    )
                else:
                    saturated[clean_tag] = new_count
                self._dirty = True
        else:
            # Successful session with interactions: reset saturation counter
            saturated = self.master_data.setdefault("saturated_tags", {})
            if clean_tag in saturated and isinstance(saturated[clean_tag], int):
                del saturated[clean_tag]
                self._dirty = True

        self.save_all()

    # ─────────────────────────────────────────────────────────────
    # Strategy 1: AI (Gemini) Persona Expansion
    # ─────────────────────────────────────────────────────────────

    def expand_via_gemini(
        self, count: int = 20, persona: Optional[str] = None
    ) -> List[str]:
        """Uses Gemini API to synthesize trending and niche-specific candidate hashtags

        aligned with the account's ai-persona.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "INSERT_YOUR_KEY_HERE":
            logger.warning("Gemini AI credential not configured. Cannot run AI expansion.")
            return []

        try:
            import google.generativeai as genai
            from dotenv import load_dotenv

            load_dotenv()
            genai.configure(api_key=api_key)
            target_persona = (
                persona
                or self.master_data.get("ai_persona")
                or "Lola the Jack Russell terrier in Perth, WA"
            )
            prompt = (
                f"You are an Instagram growth expert for the account described as: '{target_persona}'.\n"
                f"Generate {count} highly relevant, engaging, and active Instagram hashtags that this account should interact with.\n"
                f"Divide them into: 1. Local/Geographic, 2. Breed/Niche, 3. Outdoor/Lifestyle, 4. Viral/Reach.\n"
                f"Return ONLY a clean JSON object with a single key 'hashtags' containing a list of strings without '#'. Example:\n"
                f'{{"hashtags": ["perthdogs", "jackrussellmoments", "dogbeachperth"]}}'
            )

            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            text = response.text.strip()
            # Clean markdown codeblocks if present
            text = re.sub(r"^```json\s*", "", text)
            text = re.sub(r"^```\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

            data = json.loads(text)
            new_tags: List[str] = []
            for tag in data.get("hashtags", []):
                clean_tag = tag.strip().lstrip("#").lower()
                if clean_tag and self._is_relevant_tag(clean_tag):
                    tier = self._classify_tag_tier(clean_tag)
                    if self._add_tag_to_tier(tier, clean_tag):
                        new_tags.append(clean_tag)

            if new_tags:
                logger.info(
                    f"[HashtagManager] Gemini AI generated and added {len(new_tags)} new hashtags."
                )
                self.save_all()
            return new_tags
        except Exception as e:
            logger.error(f"Gemini hashtag expansion failed: {e}")
            return []

    # ─────────────────────────────────────────────────────────────
    # Persistence
    # ─────────────────────────────────────────────────────────────

    def save_all(self) -> None:
        """Atomically saves hashtags.yml and discovered_hashtags.json if dirty."""
        if not self._dirty:
            return

        try:
            if self.hashtags_yml_path:
                with atomic_write(
                    self.hashtags_yml_path, overwrite=True, encoding="utf-8"
                ) as f:
                    yaml.dump(
                        self.master_data,
                        f,
                        default_flow_style=False,
                        sort_keys=False,
                    )

            if self.discovered_path:
                with atomic_write(
                    self.discovered_path, overwrite=True, encoding="utf-8"
                ) as f:
                    json.dump(
                        self.discovered_tags, f, indent=2, sort_keys=False
                    )

            self._dirty = False
        except Exception as e:
            logger.error(f"Failed to persist hashtag manager files: {e}")
