#!/usr/bin/env python3
"""
ACP Enhanced + Agystack Interoperability Bridge for Google Antigravity.
Validates dependencies, syncs Persona D configuration, and ensures
model tier mappings between ACP taxonomy and Agystack rules.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import yaml


def get_agystack_dir() -> Path | None:
    env_plugin = os.environ.get("AGY_PLUGIN_PATH")
    if env_plugin and Path(env_plugin).is_dir():
        return Path(env_plugin).resolve()
    workspace_plugin = Path(".agents/plugins/agystack").resolve()
    if workspace_plugin.is_dir():
        return workspace_plugin
    config_root = os.environ.get("GEMINI_CONFIG_DIR")
    if config_root:
        candidate = Path(config_root) / "plugins" / "agystack"
        if candidate.is_dir():
            return candidate.resolve()
    global_plugin = (
        Path.home() / ".gemini" / "config" / "plugins" / "agystack"
    ).resolve()
    if global_plugin.is_dir():
        return global_plugin
    return None


def run_doctor() -> dict:
    agystack_dir = get_agystack_dir()
    if not agystack_dir:
        return {"error": "Agystack plugin directory not found"}

    setup_py = agystack_dir / "skills" / "setup-agystack" / "scripts" / "setup_runtime.py"
    if not setup_py.is_file():
        return {"error": f"setup_runtime.py not found at {setup_py}"}

    try:
        proc = subprocess.run(
            [sys.executable, str(setup_py), "--doctor"],
            capture_output=True,
            text=True,
            check=False,
        )
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"raw_output": proc.stdout, "returncode": proc.returncode}
    except Exception as exc:
        return {"error": str(exc)}


def check_persona_d() -> dict:
    routing_file = Path("agent/core/routing.yml")
    if not routing_file.is_file():
        return {"configured": False, "reason": "agent/core/routing.yml missing"}

    content = routing_file.read_text(encoding="utf-8")
    is_persona_d = "persona: D" in content or "persona: 'D'" in content
    has_executor = "antigravity-agystack" in content

    return {
        "configured": is_persona_d and has_executor,
        "persona_d": is_persona_d,
        "executor_set": has_executor,
    }


def check_taxonomy() -> dict:
    taxonomy_file = Path("agent/routing/taxonomy.yml")
    if not taxonomy_file.is_file():
        return {"valid": False, "reason": "agent/routing/taxonomy.yml missing"}

    try:
        data = yaml.safe_load(taxonomy_file.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"valid": False, "reason": f"YAML parse error: {exc}"}

    task_types = data.get("task_types", {})
    mappings = data.get("agystack_mappings", {})

    tier_counts = {"pro": 0, "flash": 0, "inherit": 0}
    missing_tier = []
    missing_delegation = []

    for name, spec in task_types.items():
        tier = spec.get("antigravity_tier")
        if tier in tier_counts:
            tier_counts[tier] += 1
        else:
            missing_tier.append(name)
        if "delegation_required" not in spec:
            missing_delegation.append(name)

    is_valid = (
        len(missing_tier) == 0
        and len(missing_delegation) == 0
        and len(mappings) >= 3
    )

    return {
        "valid": is_valid,
        "total_task_types": len(task_types),
        "tier_counts": tier_counts,
        "missing_tier": missing_tier,
        "missing_delegation": missing_delegation,
        "has_mappings": len(mappings) >= 3,
    }


def sync_configuration() -> bool:
    routing_file = Path("agent/core/routing.yml")
    if routing_file.is_file():
        content = routing_file.read_text(encoding="utf-8")
        if "persona: D" not in content:
            updated = (
                "# Updated per session by dispatch script, agystack setup, or manually\n"
                "# DO NOT mix static and dynamic content in the same file\n\n"
                "session:\n"
                "  executor: antigravity-agystack  # Antigravity native coordinator with poteto-agent delegation\n"
                "  model: gemini-3.8-flash        # active Antigravity session model tier or inherit\n"
                "  persona: D                     # A (copilot-only), B (deepseek-only), C (mixed), D (antigravity-agystack)\n"
            )
            routing_file.write_text(updated, encoding="utf-8")
            print("Updated agent/core/routing.yml with Persona D.")
    return True


def print_status() -> None:
    agystack_dir = get_agystack_dir()
    persona_status = check_persona_d()
    taxonomy_status = check_taxonomy()

    print("==================================================")
    print("  ACP Enhanced + Agystack Interoperability Status")
    print("==================================================")
    print(f"Agystack Plugin Path: {agystack_dir if agystack_dir else 'NOT FOUND'}")
    print(
        f"Persona D Configured: {'YES' if persona_status.get('configured') else 'NO'}"
    )
    print(
        f"Taxonomy Tier Mapping: {'YES' if taxonomy_status.get('valid') else 'NO'}"
    )
    if taxonomy_status.get("valid"):
        counts = taxonomy_status.get("tier_counts", {})
        total = taxonomy_status.get("total_task_types", 0)
        print(
            f"  - Total Task Types: {total} (pro: {counts.get('pro', 0)}, "
            f"flash: {counts.get('flash', 0)}, inherit: {counts.get('inherit', 0)})"
        )

    if agystack_dir:
        runtime_json = agystack_dir / "agystack-runtime.json"
        if runtime_json.is_file():
            try:
                cfg = json.loads(runtime_json.read_text(encoding="utf-8"))
                print(f"Active Runtime: {cfg.get('runtime', 'local')}")
                print(f"Max Local Workers: {cfg.get('max_workers', 8)}")
            except Exception:
                pass

        models_md = agystack_dir / "rules" / "agystack-models.md"
        print(f"Model Configuration: {'FOUND' if models_md.is_file() else 'MISSING'}")

    print("==================================================")


def install_to_project(target_path: str) -> bool:
    """Installs the Agystack + ACP Enhanced integration into a target project."""
    target_dir = Path(target_path).resolve()
    if not target_dir.is_dir():
        print(f"Error: Target directory does not exist: {target_dir}")
        return False

    files_to_sync = [
        ("agent/core/routing.yml", "agent/core/routing.yml"),
        ("agent/routing/taxonomy.yml", "agent/routing/taxonomy.yml"),
        ("agent/routing/rules.md", "agent/routing/rules.md"),
        ("agent/commands/acp.agystack.md", "agent/commands/acp.agystack.md"),
        ("agent/commands/acp.proceed.md", "agent/commands/acp.proceed.md"),
        ("agent/commands/acp.review.md", "agent/commands/acp.review.md"),
        (
            "agent/templates/handoff-manifest.template.md",
            "agent/templates/handoff-manifest.template.md",
        ),
        (
            "agent/wiki/cross-platform-adapters.md",
            "agent/wiki/cross-platform-adapters.md",
        ),
        (
            ".agents/skills/acp-agystack/SKILL.md",
            ".agents/skills/acp-agystack/SKILL.md",
        ),
        ("scripts/acp_agystack_bridge.py", "scripts/acp_agystack_bridge.py"),
    ]

    source_root = Path(__file__).resolve().parent.parent

    print(f"Installing Agystack + ACP integration into: {target_dir}")
    copied = 0
    for rel_src, rel_dst in files_to_sync:
        src_file = source_root / rel_src
        dst_file = target_dir / rel_dst
        if not src_file.is_file():
            print(f"  [WARN] Source file missing: {src_file}")
            continue
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_file)
        print(f"  [OK] Installed: {rel_dst}")
        copied += 1

    print(f"\nInstallation complete ({copied} files synchronized).")
    print(f"Run 'python scripts/acp_agystack_bridge.py' in {target_dir} to verify.")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="ACP Agystack Bridge")
    parser.add_argument(
        "--doctor", action="store_true", help="Run runtime dependency checks"
    )
    parser.add_argument(
        "--status", action="store_true", help="Inspect integration status"
    )
    parser.add_argument(
        "--sync", action="store_true", help="Sync Persona D configuration"
    )
    parser.add_argument(
        "--install-to",
        metavar="TARGET_DIR",
        type=str,
        help="Install Agystack + ACP integration into another project directory",
    )

    args = parser.parse_args()

    if args.install_to:
        success = install_to_project(args.install_to)
        sys.exit(0 if success else 1)

    if args.doctor:
        report = run_doctor()
        print(json.dumps(report, indent=2))
        sys.exit(0)

    if args.sync:
        sync_configuration()
        print("Synchronization complete.")
        sys.exit(0)

    print_status()


if __name__ == "__main__":
    main()
