import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import yaml


class MultiConfigValidationError(Exception):
    """Raised when multi_config.yml contains invalid structure, syntax, or values."""
    pass


@dataclass
class AccountConfig:
    username: str
    config_path: str
    device_id: str
    enabled: bool = True
    priority: int = 1
    gemini_api_key: Optional[str] = None
    working_hours: Optional[str] = None


@dataclass
class OrchestratorConfig:
    max_concurrent: int = 5
    stagger_start_seconds: str = "30-60"
    health_check_interval: int = 15
    auto_restart: bool = True
    max_restart_attempts: int = 3
    log_dir: str = "logs/orchestrator"
    global_blacklist: Optional[str] = None
    global_whitelist: Optional[str] = None


class MultiAccountConfig:
    """Loads, validates, and accesses multi-account orchestration configuration."""

    DEVICE_REGEX = re.compile(r"^(emulator-\d+|[0-9a-zA-Z._:-]+)$")

    def __init__(
        self,
        orchestrator: OrchestratorConfig,
        accounts: List[AccountConfig],
        raw_config: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
    ):
        self.orchestrator = orchestrator
        self.accounts = accounts
        self.raw_config = raw_config or {}
        self.config_path = config_path

    @classmethod
    def load(cls, path: str = "multi_config.yml") -> "MultiAccountConfig":
        """Loads and validates a multi_config.yml file."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Multi-account config file not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            raise MultiConfigValidationError(f"Failed to parse YAML in {path}: {e}") from e

        if not isinstance(data, dict):
            raise MultiConfigValidationError(
                f"Root of {path} must be a dictionary/mapping, got {type(data).__name__}"
            )

        # Parse orchestrator section
        orch_data = data.get("orchestrator", {})
        if not isinstance(orch_data, dict):
            raise MultiConfigValidationError(
                f"'orchestrator' section in {path} must be a dictionary, got {type(orch_data).__name__}"
            )

        stagger = str(orch_data.get("stagger_start_seconds", "30-60"))
        cls._validate_stagger_range(stagger)

        global_bl = orch_data.get("global_blacklist")
        global_wl = orch_data.get("global_whitelist")

        orchestrator = OrchestratorConfig(
            max_concurrent=int(orch_data.get("max_concurrent", 5)),
            stagger_start_seconds=stagger,
            health_check_interval=int(orch_data.get("health_check_interval", 15)),
            auto_restart=bool(orch_data.get("auto_restart", True)),
            max_restart_attempts=int(orch_data.get("max_restart_attempts", 3)),
            log_dir=str(orch_data.get("log_dir", "logs/orchestrator")),
            global_blacklist=str(global_bl) if global_bl else None,
            global_whitelist=str(global_wl) if global_wl else None,
        )

        # Parse accounts list
        accounts_data = data.get("accounts", [])
        if not isinstance(accounts_data, list):
            raise MultiConfigValidationError(
                f"'accounts' section in {path} must be a list, got {type(accounts_data).__name__}"
            )

        if not accounts_data:
            raise MultiConfigValidationError(
                f"'accounts' section in {path} cannot be empty. At least one account must be defined."
            )

        seen_usernames = set()
        seen_devices = set()
        accounts: List[AccountConfig] = []

        for idx, acc in enumerate(accounts_data):
            if not isinstance(acc, dict):
                raise MultiConfigValidationError(
                    f"Account entry #{idx + 1} in {path} must be a dictionary"
                )

            username = acc.get("username")
            if not username or not isinstance(username, str) or not username.strip():
                raise MultiConfigValidationError(
                    f"Account entry #{idx + 1} in {path} is missing a valid 'username'"
                )
            username = username.strip()

            if username in seen_usernames:
                raise MultiConfigValidationError(
                    f"Duplicate username detected: '{username}' is configured more than once"
                )
            seen_usernames.add(username)

            config_path_acc = acc.get("config")
            if not config_path_acc or not isinstance(config_path_acc, str):
                raise MultiConfigValidationError(
                    f"Account '{username}' in {path} is missing 'config' path"
                )
            if not os.path.exists(config_path_acc):
                raise MultiConfigValidationError(
                    f"Config file for account '{username}' does not exist: {config_path_acc}"
                )

            device_id = acc.get("device")
            if not device_id or not isinstance(device_id, str) or not device_id.strip():
                raise MultiConfigValidationError(
                    f"Account '{username}' in {path} is missing a valid 'device' identifier"
                )
            device_id = device_id.strip()

            if not cls.DEVICE_REGEX.match(device_id):
                raise MultiConfigValidationError(
                    f"Device ID '{device_id}' for account '{username}' has an invalid format. "
                    f"Expected serial like 'emulator-5554', '127.0.0.1:5555', or alphanumeric USB serial."
                )

            enabled = bool(acc.get("enabled", True))
            if enabled:
                if device_id in seen_devices:
                    raise MultiConfigValidationError(
                        f"Device collision: Device '{device_id}' is assigned to multiple enabled accounts. "
                        f"Each enabled account must have a dedicated unique device."
                    )
                seen_devices.add(device_id)

            priority = int(acc.get("priority", 1))
            gemini_key = acc.get("gemini_api_key")
            working_hours = acc.get("schedule", {}).get("working_hours") if isinstance(acc.get("schedule"), dict) else None

            accounts.append(
                AccountConfig(
                    username=username,
                    config_path=config_path_acc,
                    device_id=device_id,
                    enabled=enabled,
                    priority=priority,
                    gemini_api_key=str(gemini_key) if gemini_key else None,
                    working_hours=str(working_hours) if working_hours else None,
                )
            )

        return cls(
            orchestrator=orchestrator,
            accounts=accounts,
            raw_config=data,
            config_path=path,
        )

    @classmethod
    def _validate_stagger_range(cls, stagger: str) -> None:
        """Validates that stagger_start_seconds is a positive int or min-max range."""
        if "-" in stagger:
            parts = stagger.split("-")
            if len(parts) != 2:
                raise MultiConfigValidationError(
                    f"Invalid stagger_start_seconds format: '{stagger}'. Expected 'min-max' (e.g. '30-60') or single integer."
                )
            try:
                min_val = int(parts[0].strip())
                max_val = int(parts[1].strip())
            except ValueError:
                raise MultiConfigValidationError(
                    f"Non-integer values in stagger_start_seconds: '{stagger}'"
                )
            if min_val < 0 or max_val < 0:
                raise MultiConfigValidationError(
                    f"stagger_start_seconds must be positive: '{stagger}'"
                )
            if min_val > max_val:
                raise MultiConfigValidationError(
                    f"stagger_start_seconds min ({min_val}) cannot be greater than max ({max_val})"
                )
        else:
            try:
                val = int(stagger.strip())
                if val < 0:
                    raise MultiConfigValidationError(
                        f"stagger_start_seconds must be positive: '{stagger}'"
                    )
            except ValueError:
                raise MultiConfigValidationError(
                    f"Invalid stagger_start_seconds value: '{stagger}'"
                )

    def get_enabled_accounts(self) -> List[AccountConfig]:
        """Returns enabled accounts sorted by priority (lowest number first, e.g. 1 then 2)."""
        return sorted(
            [acc for acc in self.accounts if acc.enabled],
            key=lambda x: x.priority,
        )

    def get_account(self, username: str) -> Optional[AccountConfig]:
        """Finds an account by username."""
        clean_user = username.lstrip("@").strip().lower()
        for acc in self.accounts:
            if acc.username.lstrip("@").strip().lower() == clean_user:
                return acc
        return None
