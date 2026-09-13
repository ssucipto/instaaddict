import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DogfoodOptimizer:
    """Self-learning / dog-feeding analyzer that inspects session data,

    execution history, and error trace logs to synthesize concrete config
    tuning recommendations.
    """

    def __init__(self, username: str):
        self.username = username
        self.account_dir = os.path.join("accounts", username)
        self.sessions_path = os.path.join(self.account_dir, "sessions.json")
        self.history_path = os.path.join(self.account_dir, "history.md")
        self.error_log_path = os.path.join("logs", f"{username}_error_trace.log")
        self.suggestions_json_path = os.path.join(
            self.account_dir, "tuning_suggestions.json"
        )
        self.suggestions_md_path = os.path.join(
            self.account_dir, "tuning_suggestions.md"
        )

    def analyze(self) -> Dict[str, Any]:
        """Runs the dog-feeding diagnostic and outputs tuning suggestions."""
        sessions = self._load_sessions()
        error_diagnostics = self._analyze_error_log()

        total_sessions = len(sessions)
        total_interactions = sum(s.get("total_interactions", 0) for s in sessions)
        successful_interactions = sum(
            s.get("successful_interactions", 0) for s in sessions
        )
        total_likes = sum(s.get("total_likes", 0) for s in sessions)
        total_followed = sum(s.get("total_followed", 0) for s in sessions)
        total_crashes = sum(s.get("total_crashes", 0) for s in sessions)
        total_uploads_success = sum(s.get("total_uploads_success", 0) for s in sessions)
        total_uploads_failed = sum(s.get("total_uploads_failed", 0) for s in sessions)

        success_rate = (
            round((successful_interactions / total_interactions) * 100, 1)
            if total_interactions > 0
            else 0.0
        )

        recommendations: List[Dict[str, Any]] = []

        # 1. Evaluate Quota / Rate-limit Hotspots
        if error_diagnostics.get("quota_429_errors", 0) > 0:
            recommendations.append(
                {
                    "category": "Vision AI Quota",
                    "severity": "HIGH",
                    "issue": f"Detected {error_diagnostics['quota_429_errors']} Gemini API 429 quota exhaustion events.",
                    "action": "Lower --evaluate-percentage in config.yml (e.g., from 100 to 50) and reduce reels speed.",
                    "parameter": "evaluate-percentage",
                    "suggested_value": 50,
                }
            )

        # 2. Evaluate Crash Frequency
        if total_crashes > 0 or error_diagnostics.get("fatal_crashes", 0) > 0:
            recommendations.append(
                {
                    "category": "Stability & Timing",
                    "severity": "MEDIUM",
                    "issue": f"Recorded {total_crashes} session crashes and {error_diagnostics.get('fatal_crashes', 0)} fatal exceptions.",
                    "action": "Increase inter-interaction delays to allow slow network rendering and avoid UI timeouts.",
                    "parameter": "delay-mean",
                    "suggested_value": "increase by 2.0s",
                }
            )

        # 3. Evaluate Interaction Success Rate
        if total_interactions > 20 and success_rate < 40.0:
            recommendations.append(
                {
                    "category": "Interaction Quality",
                    "severity": "MEDIUM",
                    "issue": f"Interaction success rate is low ({success_rate}%). Many targets fail filter or limit checks.",
                    "action": "Review filters.yml (relax follower/following ratio) or rotate target hashtags/bloggers.",
                    "parameter": "filters.yml",
                    "suggested_value": "Relax min_followers / max_following filters",
                }
            )

        # 4. Evaluate Content Upload Pipeline
        if total_uploads_failed > 0:
            recommendations.append(
                {
                    "category": "Content Queue Uploads",
                    "severity": "HIGH",
                    "issue": f"Encountered {total_uploads_failed} failed upload attempts.",
                    "action": "Inspect format and resolution of queued media files in content_queue/pending.",
                    "parameter": "content_queue",
                    "suggested_value": "Ensure media files are standard 1:1 or 9:16 jpg/mp4",
                }
            )

        # Default recommendation if performance is nominal
        if not recommendations:
            recommendations.append(
                {
                    "category": "General Performance",
                    "severity": "INFO",
                    "issue": "Nominal bot operations with no abnormal crash or quota failure patterns.",
                    "action": "Current parameters are well-balanced. Continue monitored runs.",
                    "parameter": "status",
                    "suggested_value": "maintain",
                }
            )

        report_data = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "username": self.username,
            "metrics": {
                "total_sessions": total_sessions,
                "total_interactions": total_interactions,
                "successful_interactions": successful_interactions,
                "success_rate_percent": success_rate,
                "total_likes": total_likes,
                "total_followed": total_followed,
                "total_crashes": total_crashes,
                "total_uploads_success": total_uploads_success,
                "total_uploads_failed": total_uploads_failed,
            },
            "error_diagnostics": error_diagnostics,
            "recommendations": recommendations,
        }

        self._save_suggestions(report_data)
        return report_data

    def _load_sessions(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.sessions_path):
            try:
                with open(self.sessions_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading {self.sessions_path}: {e}")
        return []

    def _analyze_error_log(self) -> Dict[str, Any]:
        stats = {
            "total_warnings": 0,
            "total_errors": 0,
            "total_criticals": 0,
            "quota_429_errors": 0,
            "ui_not_found_errors": 0,
            "fatal_crashes": 0,
        }

        if not os.path.exists(self.error_log_path):
            return stats

        try:
            with open(self.error_log_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if "WARNING" in line:
                        stats["total_warnings"] += 1
                    elif "ERROR" in line:
                        stats["total_errors"] += 1
                    elif "CRITICAL" in line:
                        stats["total_criticals"] += 1

                    if "429" in line or "QuotaExceeded" in line:
                        stats["quota_429_errors"] += 1
                    if "UiObjectNotFoundError" in line or "Cannot find" in line:
                        stats["ui_not_found_errors"] += 1
                    if "Uncaught fatal exception" in line or "Traceback" in line:
                        stats["fatal_crashes"] += 1
        except Exception as e:
            logger.debug(f"Failed scanning error trace log: {e}")

        return stats

    def _save_suggestions(self, data: Dict[str, Any]) -> None:
        """Writes suggestions to JSON and formatted Markdown."""
        try:
            with open(self.suggestions_json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed writing {self.suggestions_json_path}: {e}")

        try:
            with open(self.suggestions_md_path, "w", encoding="utf-8") as f:
                f.write(f"# Dogfooding Optimization Report: @{self.username}\n\n")
                f.write(f"Generated on: `{data['generated_at']}`\n\n")
                f.write("## 1. Performance Overview\n")
                metrics = data["metrics"]
                f.write(f"- **Total Sessions Analyzed**: {metrics['total_sessions']}\n")
                f.write(
                    f"- **Success Rate**: {metrics['success_rate_percent']}% ({metrics['successful_interactions']}/{metrics['total_interactions']})\n"
                )
                f.write(f"- **Total Likes**: {metrics['total_likes']}\n")
                f.write(f"- **Total Follows**: {metrics['total_followed']}\n")
                f.write(f"- **Total Crashes**: {metrics['total_crashes']}\n")
                f.write(
                    f"- **Uploaded Posts**: {metrics['total_uploads_success']} succeeded, {metrics['total_uploads_failed']} failed\n\n"
                )

                f.write("## 2. Error Diagnostics\n")
                errs = data["error_diagnostics"]
                f.write(f"- Warnings: {errs['total_warnings']}\n")
                f.write(f"- Errors: {errs['total_errors']}\n")
                f.write(f"- API 429 Quota Events: {errs['quota_429_errors']}\n")
                f.write(
                    f"- UI Element Not Found Events: {errs['ui_not_found_errors']}\n"
                )
                f.write(f"- Fatal Exceptions: {errs['fatal_crashes']}\n\n")

                f.write("## 3. Actionable Tuning Recommendations\n")
                f.write("| Severity | Category | Issue | Recommended Action |\n")
                f.write("|---|---|---|---|\n")
                for r in data["recommendations"]:
                    f.write(
                        f"| **{r['severity']}** | {r['category']} | {r['issue']} | {r['action']} |\n"
                    )

                f.write("\n## 4. How to Dog-feed to an LLM\n")
                f.write(
                    "You can paste this file or `tuning_suggestions.json` directly into an agent turn to automatically re-balance your `config.yml`.\n"
                )
        except Exception as e:
            logger.error(f"Failed writing {self.suggestions_md_path}: {e}")


def run_dogfood_optimization(username: str) -> Optional[Dict[str, Any]]:
    """Helper entry point to trigger dogfood analysis for an account."""
    if not username:
        return None
    optimizer = DogfoodOptimizer(username)
    return optimizer.analyze()
