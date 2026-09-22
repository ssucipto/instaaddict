import json
import logging
import os
import re
import shutil
import time
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
        self.config_path = os.path.join(self.account_dir, "config.yml")
        self.filters_path = os.path.join(self.account_dir, "filters.yml")

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
        total_subscreen_escapes = sum(
            s.get("total_subscreen_escapes", 0) for s in sessions
        )
        total_uploads_success = sum(s.get("total_uploads_success", 0) for s in sessions)
        total_uploads_failed = sum(s.get("total_uploads_failed", 0) for s in sessions)

        # Aggregate granular filter skip reasons across sessions
        total_skip_reasons: Dict[str, int] = {}
        for s in sessions:
            for r_k, r_v in s.get("skip_reasons", {}).items():
                total_skip_reasons[r_k] = total_skip_reasons.get(r_k, 0) + int(r_v)
        total_skips = sum(total_skip_reasons.values())

        # Aggregate job execution yield and standards across sessions
        aggregated_jobs: Dict[str, Dict[str, Any]] = {}
        for s in sessions:
            for j_name, j_data in s.get("job_metrics", {}).items():
                if j_name not in aggregated_jobs:
                    aggregated_jobs[j_name] = {
                        "runs": 0,
                        "duration_seconds": 0.0,
                        "interactions_attempted": 0,
                        "interactions_successful": 0,
                        "followed": 0,
                        "scraped": 0,
                    }
                aggregated_jobs[j_name]["runs"] += 1
                aggregated_jobs[j_name]["duration_seconds"] += j_data.get(
                    "duration_seconds", 0.0
                )
                aggregated_jobs[j_name]["interactions_attempted"] += j_data.get(
                    "interactions_attempted", 0
                )
                aggregated_jobs[j_name]["interactions_successful"] += j_data.get(
                    "interactions_successful", 0
                )
                aggregated_jobs[j_name]["followed"] += j_data.get("followed", 0)
                aggregated_jobs[j_name]["scraped"] += j_data.get("scraped", 0)

        # Aggregate crash foreground and context telemetry
        aggregated_crashes: Dict[str, int] = {}
        for s in sessions:
            for c in s.get("crash_history", []):
                pkg = c.get("foreground_package") or "unknown"
                aggregated_crashes[pkg] = aggregated_crashes.get(pkg, 0) + 1

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
                    "issue": (
                        f"Recorded {total_crashes} session crashes and "
                        f"{error_diagnostics.get('fatal_crashes', 0)} fatal exceptions."
                    ),
                    "action": "Increase inter-interaction delays to allow slow network rendering and avoid UI timeouts.",
                    "parameter": "delay-mean",
                    "suggested_value": "increase by 2.0s",
                }
            )

        # 3. Evaluate Filter Rejections & Starvation Patterns
        if total_skips > 0:
            lt_fol = total_skip_reasons.get("LT_FOLLOWERS", 0)
            if lt_fol / total_skips >= 0.30:
                pct = round(lt_fol / total_skips * 100, 1)
                recommendations.append(
                    {
                        "category": "Filter Starvation",
                        "severity": "HIGH" if pct >= 50.0 else "MEDIUM",
                        "issue": f"{pct}% ({lt_fol}/{total_skips}) of profile rejections were caused by min_followers.",
                        "action": "Lower min_followers in filters.yml (e.g., reduce by 30-50%) to unblock candidate throughput.",
                        "parameter": "min_followers",
                        "suggested_value": "lower by 30-50%",
                    }
                )

            pot_ratio = total_skip_reasons.get("POTENCY_RATIO", 0)
            if pot_ratio / total_skips >= 0.25:
                pct = round(pot_ratio / total_skips * 100, 1)
                recommendations.append(
                    {
                        "category": "Filter Starvation",
                        "severity": "MEDIUM",
                        "issue": f"{pct}% ({pot_ratio}/{total_skips}) of profile rejections failed potency ratio bounds.",
                        "action": "Relax min_potency_ratio in filters.yml (e.g., reduce to 0.1-0.2) to accept wider creator pools.",
                        "parameter": "min_potency_ratio",
                        "suggested_value": "0.1-0.2",
                    }
                )

            biz_count = total_skip_reasons.get("HAS_BUSINESS", 0)
            if biz_count / total_skips >= 0.25:
                pct = round(biz_count / total_skips * 100, 1)
                recommendations.append(
                    {
                        "category": "Filter Starvation",
                        "severity": "MEDIUM",
                        "issue": f"{pct}% ({biz_count}/{total_skips}) of profile rejections were flagged as business accounts.",
                        "action": "Set skip_business: false in filters.yml to permit interaction with creator/business accounts.",
                        "parameter": "skip_business",
                        "suggested_value": "false",
                    }
                )

            posts_count = total_skip_reasons.get("NOT_ENOUGH_POSTS", 0)
            if posts_count / total_skips >= 0.20:
                pct = round(posts_count / total_skips * 100, 1)
                recommendations.append(
                    {
                        "category": "Filter Starvation",
                        "severity": "LOW",
                        "issue": f"{pct}% ({posts_count}/{total_skips}) of profile rejections lacked minimum post counts.",
                        "action": "Lower min_posts in filters.yml (e.g., set to 1) to interact with newer accounts.",
                        "parameter": "min_posts",
                        "suggested_value": "1",
                    }
                )

            lang_count = total_skip_reasons.get("BIOGRAPHY_LANGUAGE_NOT_MATCH", 0)
            if lang_count / total_skips >= 0.20:
                pct = round(lang_count / total_skips * 100, 1)
                recommendations.append(
                    {
                        "category": "Filter Starvation",
                        "severity": "MEDIUM",
                        "issue": f"{pct}% ({lang_count}/{total_skips}) of profile rejections failed biography language checks.",
                        "action": "Broaden biography_language in filters.yml or remove language constraints.",
                        "parameter": "biography_language",
                        "suggested_value": "broaden languages",
                    }
                )
        elif total_interactions > 20 and success_rate < 40.0:
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

        # 4. Evaluate Job / Task Performance Standards
        for j_name, j_data in aggregated_jobs.items():
            att = j_data.get("interactions_attempted", 0)
            succ = j_data.get("interactions_successful", 0)
            dur = j_data.get("duration_seconds", 0.0)
            if att >= 5 and succ == 0:
                recommendations.append(
                    {
                        "category": "Task Performance Standards",
                        "severity": "HIGH",
                        "issue": f"Job '{j_name}' attempted {att} interactions with 0 successes (100% failure rate).",
                        "action": f"Refresh source targets or relax filter constraints for '{j_name}'. Source accounts/tags may be depleted or protected.",
                        "parameter": f"job.{j_name}",
                        "suggested_value": "rotate sources",
                    }
                )
            elif dur > 300.0 and att == 0:
                recommendations.append(
                    {
                        "category": "Task Performance Standards",
                        "severity": "MEDIUM",
                        "issue": f"Job '{j_name}' ran for {round(dur, 1)}s without finding any interaction targets.",
                        "action": f"Verify sources pool for '{j_name}' or check UI layout compatibility.",
                        "parameter": f"job.{j_name}",
                        "suggested_value": "check sources pool",
                    }
                )

        # 5. Evaluate Crash Forensics & Foreground State
        launcher_crashes = (
            aggregated_crashes.get("com.android.launcher", 0)
            + aggregated_crashes.get("com.android.systemui", 0)
        )
        if launcher_crashes > 0:
            recommendations.append(
                {
                    "category": "Crash Forensics",
                    "severity": "HIGH",
                    "issue": f"Detected {launcher_crashes} crash event(s) where device was displaced to Android launcher/system UI.",
                    "action": "Instagram process was killed or displaced by OS/watchdog back keys. Check emulator RAM and ensure watchdog heartbeat instrumentation.",
                    "parameter": "watchdog_and_ram",
                    "suggested_value": "allocate >= 3GB RAM to emulator",
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

        # 5. Evaluate Subscreen Escape Failures
        if error_diagnostics.get("subscreen_escape_failures", 0) > 0:
            recommendations.append(
                {
                    "category": "Navigation & Subscreens",
                    "severity": "HIGH",
                    "issue": f"Detected {error_diagnostics['subscreen_escape_failures']} failure(s) escaping deep subscreens.",
                    "action": (
                        "Increase inter-interaction delays to allow screen settles and "
                        "inspect for unhandled modal popups."
                    ),
                    "parameter": "delay-mean",
                    "suggested_value": "increase by 1.5s",
                }
            )

        # 6. Evaluate Restart Profile Failures
        if error_diagnostics.get("restart_profile_failures", 0) > 0:
            recommendations.append(
                {
                    "category": "Restart & Recovery",
                    "severity": "HIGH",
                    "issue": (
                        f"Detected {error_diagnostics['restart_profile_failures']} "
                        "failure(s) navigating to profile after bot restart."
                    ),
                    "action": "Increase startup settle timeout or check device/emulator uiautomator2 server stability.",
                    "parameter": "open_instagram_settle",
                    "suggested_value": "verify emulator uiautomator2 health",
                }
            )

        # 7. Evaluate Performance Telemetry & Motion Dynamics
        telemetry_metrics: Dict[str, Any] = {}
        try:
            from InstaAddict.core.telemetry import PerformanceTracker

            tracker = PerformanceTracker.get_instance()
            motion_summary = tracker.get_motion_summary()
            percentiles = tracker.get_percentiles()
            telemetry_metrics = {
                "motion": motion_summary,
                "percentiles": percentiles,
            }

            if motion_summary.get("total_swipes", 0) >= 5:
                eff = motion_summary.get("displacement_efficiency_pct", 100.0)
                zero_disp = motion_summary.get("zero_displacement_swipes", 0)
                if eff < 70.0:
                    recommendations.append(
                        {
                            "category": "Motion & Viewport",
                            "severity": "MEDIUM",
                            "issue": (
                                f"Viewport displacement efficiency is {eff}% "
                                f"({zero_disp} zero-displacement swipes detected)."
                            ),
                            "action": "Verify swipe coordinates, boundary resistance, or device resolution scaling.",
                            "parameter": "viewport_swipe",
                            "suggested_value": "adjust coordinates",
                        }
                    )

            profile_p95 = percentiles.get("view.profile_load", {}).get("p95", 0.0)
            if profile_p95 > 4000.0:
                recommendations.append(
                    {
                        "category": "UI Latency",
                        "severity": "MEDIUM",
                        "issue": f"Profile load P95 tail latency is elevated ({profile_p95}ms).",
                        "action": "Increase speed delay-mean to allow UI settling before interaction.",
                        "parameter": "delay-mean",
                        "suggested_value": "increase by 1.0s",
                    }
                )

            vision_p95 = percentiles.get("api.gemini_vision", {}).get("p95", 0.0)
            if vision_p95 > 15000.0:
                recommendations.append(
                    {
                        "category": "Vision AI",
                        "severity": "LOW",
                        "issue": f"Gemini Vision API P95 latency is high ({vision_p95}ms).",
                        "action": "Network latency or payload size delay detected. Consider thumbnail resolution optimization.",
                        "parameter": "gemini_timeout",
                        "suggested_value": "30.0",
                    }
                )
        except Exception as e:
            logger.debug(f"Telemetry analysis skipped: {e}")

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
                "total_subscreen_escapes": total_subscreen_escapes,
                "total_uploads_success": total_uploads_success,
                "total_uploads_failed": total_uploads_failed,
                "total_skips": total_skips,
            },
            "skip_reasons": total_skip_reasons,
            "job_performance": aggregated_jobs,
            "crash_diagnostics_extended": aggregated_crashes,
            "telemetry": telemetry_metrics,
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
            "subscreen_escapes": 0,
            "subscreen_escape_failures": 0,
            "restart_profile_failures": 0,
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
                    if "Tab bar not visible (screen in subscreen)" in line:
                        stats["subscreen_escapes"] += 1
                    if "Could not restore tab bar after" in line:
                        stats["subscreen_escape_failures"] += 1
                    if "Failed to navigate to profile after restart" in line:
                        stats["restart_profile_failures"] += 1
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
                rate_str = (
                    f"{metrics['success_rate_percent']}% "
                    f"({metrics['successful_interactions']}/{metrics['total_interactions']})"
                )
                f.write(f"- **Success Rate**: {rate_str}\n")
                f.write(f"- **Total Likes**: {metrics['total_likes']}\n")
                f.write(f"- **Total Follows**: {metrics['total_followed']}\n")
                f.write(f"- **Total Crashes**: {metrics['total_crashes']}\n")
                f.write(
                    f"- **Total Subscreen Escapes**: {metrics.get('total_subscreen_escapes', 0)}\n"
                )
                f.write(
                    f"- **Uploaded Posts**: {metrics['total_uploads_success']} succeeded, "
                    f"{metrics['total_uploads_failed']} failed\n\n"
                )

                f.write("## 2. Error Diagnostics\n")
                errs = data["error_diagnostics"]
                f.write(f"- Warnings: {errs['total_warnings']}\n")
                f.write(f"- Errors: {errs['total_errors']}\n")
                f.write(f"- API 429 Quota Events: {errs['quota_429_errors']}\n")
                f.write(
                    f"- UI Element Not Found Events: {errs['ui_not_found_errors']}\n"
                )
                f.write(f"- Fatal Exceptions: {errs['fatal_crashes']}\n")
                f.write(f"- Subscreen Escapes: {errs.get('subscreen_escapes', 0)}\n")
                f.write(
                    f"- Subscreen Escape Failures: {errs.get('subscreen_escape_failures', 0)}\n"
                )
                f.write(
                    f"- Restart Profile Failures: {errs.get('restart_profile_failures', 0)}\n\n"
                )

                sec_idx = 3
                if "skip_reasons" in data and data["skip_reasons"]:
                    f.write(f"## {sec_idx}. Filter Rejection Distribution & Starvation Analysis\n")
                    f.write("| Skip Reason | Count | Percentage |\n")
                    f.write("|---|---|---|\n")
                    t_skips = sum(data["skip_reasons"].values())
                    for r_name, r_count in sorted(
                        data["skip_reasons"].items(), key=lambda x: x[1], reverse=True
                    ):
                        pct_s = f"{round((r_count / max(t_skips, 1)) * 100, 1)}%"
                        f.write(f"| `{r_name}` | {r_count} | {pct_s} |\n")
                    f.write("\n")
                    sec_idx += 1

                if "job_performance" in data and data["job_performance"]:
                    f.write(f"## {sec_idx}. Job & Task Performance Standards\n")
                    f.write("| Job Name | Runs | Duration (s) | Attempted | Successful | Yield % |\n")
                    f.write("|---|---|---|---|---|---|\n")
                    for j_n, j_d in sorted(data["job_performance"].items()):
                        att = j_d.get("interactions_attempted", 0)
                        succ = j_d.get("interactions_successful", 0)
                        yield_pct = (
                            f"{round((succ / max(att, 1)) * 100, 1)}%"
                            if att > 0
                            else "N/A"
                        )
                        dur_s = round(j_d.get("duration_seconds", 0.0), 1)
                        f.write(
                            f"| `{j_n}` | {j_d.get('runs', 0)} | {dur_s} | {att} | {succ} | {yield_pct} |\n"
                        )
                    f.write("\n")
                    sec_idx += 1

                if "telemetry" in data and data["telemetry"]:
                    f.write(f"## {sec_idx}. Telemetry & Latency Diagnostics\n")
                    telem = data["telemetry"]
                    if "motion" in telem and telem["motion"]:
                        mot = telem["motion"]
                        f.write(
                            f"- **Motion Efficiency**: {mot.get('displacement_efficiency_pct', 100)}% "
                            f"({mot.get('displaced_swipes', 0)}/{mot.get('total_swipes', 0)} displaced, "
                            f"{mot.get('zero_displacement_swipes', 0)} zero-disp, "
                            f"{mot.get('snapback_events', 0)} snapbacks)\n"
                        )
                    if "percentiles" in telem and telem["percentiles"]:
                        f.write("- **Operation Latencies**:\n")
                        for op_k, op_v in telem["percentiles"].items():
                            f.write(
                                f"  - `{op_k}`: P50={op_v.get('p50', 0)}ms, "
                                f"P95={op_v.get('p95', 0)}ms, avg={op_v.get('avg', 0)}ms\n"
                            )
                    f.write("\n")
                    sec_idx += 1

                f.write(f"## {sec_idx}. Actionable Tuning Recommendations\n")
                f.write("| Severity | Category | Issue | Recommended Action |\n")
                f.write("|---|---|---|---|\n")
                for r in data["recommendations"]:
                    f.write(
                        f"| **{r['severity']}** | {r['category']} | {r['issue']} | {r['action']} |\n"
                    )

                sec_idx += 1
                f.write(f"\n## {sec_idx}. How to Dog-feed to an LLM\n")
                f.write(
                    "You can paste this file or `tuning_suggestions.json` directly into "
                    "an agent turn to automatically re-balance your `config.yml`.\n"
                )
        except Exception as e:
            logger.error(f"Failed writing {self.suggestions_md_path}: {e}")

    def apply_tuning(self, dry_run: bool = False, backup: bool = True) -> Dict[str, Any]:
        """Applies closed-loop configuration tuning to config.yml with comments preserved and backups created."""
        result: Dict[str, Any] = {
            "applied": [],
            "backup_file": None,
            "dry_run": dry_run,
            "config_path": self.config_path,
        }

        analysis = self.analyze()
        recommendations = analysis.get("recommendations", [])
        params_to_adjust: Dict[str, Any] = {}

        for rec in recommendations:
            param = rec.get("parameter")
            if param == "delay-mean":
                params_to_adjust["delay-mean"] = 1.0
            elif param in ("evaluate-percentage", "reels_evaluate_percentage"):
                params_to_adjust["evaluate-percentage"] = -15
            elif param == "min_followers":
                params_to_adjust["min_followers"] = 0.7

        if not params_to_adjust:
            logger.info("[AUTOTUNE] No actionable parameter tuning required at this time.")
            return result

        if not os.path.exists(self.config_path) and not os.path.exists(self.filters_path):
            logger.warning(
                f"[AUTOTUNE] Neither {self.config_path} nor {self.filters_path} found. Skipping auto-tune."
            )
            result["error"] = "config_not_found"
            return result

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except Exception as e:
                logger.error(f"[AUTOTUNE] Failed reading {self.config_path}: {e}")
                result["error"] = str(e)
                lines = []

            modified = False
            new_lines = []

            for line in lines:
                new_line = line
                # Check delay-mean
                if "delay-mean" in params_to_adjust:
                    m = re.match(r"^(\s*delay-mean\s*:\s*)([0-9.]+)(.*)$", line)
                    if m:
                        prefix, curr_val, suffix = (
                            m.group(1),
                            float(m.group(2)),
                            m.group(3),
                        )
                        new_val = min(
                            15.0,
                            max(1.0, round(curr_val + params_to_adjust["delay-mean"], 2)),
                        )
                        if new_val != curr_val:
                            new_line = (
                                f"{prefix}{new_val}{suffix}\n"
                                if not suffix.endswith("\n")
                                else f"{prefix}{new_val}{suffix}"
                            )
                            result["applied"].append(
                                {
                                    "parameter": "delay-mean",
                                    "old_value": curr_val,
                                    "new_value": new_val,
                                }
                            )
                            modified = True

                # Check evaluate-percentage / reels_evaluate_percentage
                if "evaluate-percentage" in params_to_adjust:
                    m = re.match(
                        r"^(\s*(?:evaluate-percentage|reels_evaluate_percentage)\s*:\s*)([0-9]+)(.*)$",
                        line,
                    )
                    if m:
                        prefix, curr_val, suffix = (
                            m.group(1),
                            int(m.group(2)),
                            m.group(3),
                        )
                        new_val = min(
                            100, max(20, curr_val + params_to_adjust["evaluate-percentage"])
                        )
                        if new_val != curr_val:
                            new_line = (
                                f"{prefix}{new_val}{suffix}\n"
                                if not suffix.endswith("\n")
                                else f"{prefix}{new_val}{suffix}"
                            )
                            result["applied"].append(
                                {
                                    "parameter": prefix.strip().rstrip(":"),
                                    "old_value": curr_val,
                                    "new_value": new_val,
                                }
                            )
                            modified = True

                new_lines.append(new_line)

            if modified and not dry_run:
                if backup:
                    backup_path = f"{self.config_path}.bak_{int(time.time())}"
                    try:
                        shutil.copy2(self.config_path, backup_path)
                        result["backup_file"] = backup_path
                        logger.info(f"[AUTOTUNE] Backup created at {backup_path}")
                    except Exception as e:
                        logger.error(f"[AUTOTUNE] Failed creating backup: {e}")

                try:
                    with open(self.config_path, "w", encoding="utf-8") as f:
                        f.writelines(new_lines)
                    logger.info(
                        f"[AUTOTUNE] Successfully applied tuning to {self.config_path}: {result['applied']}"
                    )
                except Exception as e:
                    logger.error(
                        f"[AUTOTUNE] Failed writing updated config {self.config_path}: {e}"
                    )
                    result["error"] = str(e)

        # Auto-tune filters.yml if filter starvation is detected
        if "min_followers" in params_to_adjust and os.path.exists(self.filters_path):
            try:
                with open(self.filters_path, "r", encoding="utf-8") as f:
                    f_lines = f.readlines()
                f_modified = False
                f_new_lines = []
                for line in f_lines:
                    m = re.match(r"^(\s*min_followers\s*:\s*)([0-9]+)(.*)$", line)
                    if m:
                        prefix, curr_val, suffix = m.group(1), int(m.group(2)), m.group(3)
                        new_val = max(5, int(curr_val * params_to_adjust["min_followers"]))
                        if new_val != curr_val:
                            line = (
                                f"{prefix}{new_val}{suffix}\n"
                                if not suffix.endswith("\n")
                                else f"{prefix}{new_val}{suffix}"
                            )
                            result["applied"].append(
                                {
                                    "file": "filters.yml",
                                    "parameter": "min_followers",
                                    "old_value": curr_val,
                                    "new_value": new_val,
                                }
                            )
                            f_modified = True
                    f_new_lines.append(line)
                if f_modified and not dry_run:
                    if backup:
                        f_bak = f"{self.filters_path}.bak_{int(time.time())}"
                        try:
                            shutil.copy2(self.filters_path, f_bak)
                            result["filters_backup_file"] = f_bak
                            logger.info(f"[AUTOTUNE] Filters backup created at {f_bak}")
                        except Exception as e:
                            logger.error(f"[AUTOTUNE] Failed creating filters backup: {e}")
                    with open(self.filters_path, "w", encoding="utf-8") as f:
                        f.writelines(f_new_lines)
                    logger.info("[AUTOTUNE] Successfully tuned filters.yml min_followers")
            except Exception as e:
                logger.error(f"[AUTOTUNE] Failed tuning filters.yml: {e}")

        return result


def run_dogfood_optimization(
    username: str, auto_tune: bool = False
) -> Optional[Dict[str, Any]]:
    """Helper entry point to trigger dogfood analysis for an account."""
    if not username:
        return None
    optimizer = DogfoodOptimizer(username)
    report = optimizer.analyze()
    if auto_tune:
        tune_res = optimizer.apply_tuning()
        if report:
            report["auto_tune_result"] = tune_res
    return report
