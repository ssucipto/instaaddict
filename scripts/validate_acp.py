import os
import re
import sys
import yaml

errors = []
warnings = []

# 1. Directory Structure
required_dirs = [
    "agent",
    "agent/design",
    "agent/milestones",
    "agent/commands",
    "agent/memory",
]
for d in required_dirs:
    if not os.path.isdir(d):
        errors.append(f"Missing required directory: {d}")

# 2. progress.yaml
if not os.path.isfile("agent/progress.yaml"):
    errors.append("Missing agent/progress.yaml")
    prog = {}
else:
    try:
        with open("agent/progress.yaml", "r", encoding="utf-8") as f:
            prog = yaml.safe_load(f)
        print("PASS: agent/progress.yaml syntax valid")
    except Exception as e:
        errors.append(f"agent/progress.yaml parse error: {e}")
        prog = {}

# 2b. Memory YAML
for mem_file in [
    "agent/memory/patterns.md",
    "agent/memory/sessions.md",
    "agent/memory/audit-carryovers.md",
]:
    if os.path.isfile(mem_file):
        try:
            with open(mem_file, "r", encoding="utf-8") as f:
                list(yaml.safe_load_all(f.read()))
            print(f"PASS: {mem_file} syntax valid")
        except Exception as e:
            errors.append(f"{mem_file} parse error: {e}")

# 2c. Version Consistency
canonical_ver = str(prog.get("project", {}).get("version", ""))
if os.path.isfile("InstaAddict/__init__.py"):
    with open("InstaAddict/__init__.py", "r", encoding="utf-8") as f:
        m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', f.read())
        init_ver = m.group(1) if m else None
        if init_ver != canonical_ver:
            errors.append(
                f"Version mismatch: progress.yaml ({canonical_ver}) vs InstaAddict/__init__.py ({init_ver})"
            )
        else:
            print(f"PASS: Version consistency verified (v{canonical_ver})")

# 2e & 2f. Milestone cross-layer status and file pointers
for ms in prog.get("milestones", []):
    m_id = ms.get("id")
    m_status = ms.get("status")
    f_path = ms.get("file")
    if f_path:
        if not os.path.isfile(f_path):
            errors.append(f"Dangling pointer in milestone {m_id}: {f_path}")
        else:
            with open(f_path, "r", encoding="utf-8") as mf:
                m_content = mf.read()
            match = re.search(r"\*\*Status\*\*:\s*([^\n\r]+)", m_content, re.IGNORECASE)
            if not match:
                match = re.search(r"status:\s*([^\n\r]+)", m_content, re.IGNORECASE)
            if match:
                raw_val = match.group(1).strip()
                doc_status = raw_val.lower()
                norm_doc = (
                    "completed"
                    if doc_status in ["completed", "implemented", "done"]
                    else (
                        "in_progress"
                        if doc_status in ["active", "in_progress"]
                        else doc_status
                    )
                )
                norm_prog = (
                    "completed"
                    if m_status in ["completed", "implemented", "done"]
                    else (
                        "in_progress"
                        if m_status in ["active", "in_progress"]
                        else m_status
                    )
                )
                if norm_doc != norm_prog:
                    errors.append(
                        f"Status mismatch for {m_id}: progress.yaml={m_status}, {f_path}={doc_status}"
                    )
            else:
                warnings.append(f"No status found in {f_path}")

# Task file pointers
for m_key, tasks in prog.get("tasks", {}).items():
    for t in tasks:
        t_id = t.get("id")
        f_path = t.get("file")
        if f_path and f_path != "null" and not os.path.isfile(f_path):
            errors.append(f"Dangling task file pointer in {t_id}: {f_path}")

print("----------------------------------------")
print(f"ACP Validation Summary: {len(errors)} error(s), {len(warnings)} warning(s)")
for w in warnings:
    print(f"  WARN: {w}")
for e in errors:
    print(f"  ERROR: {e}")

if errors:
    sys.exit(1)
print("ALL CHECKS PASSED: ACP documentation is consistent and valid.")
