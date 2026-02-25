"""Productivity: TODO scanner, PR checker."""

import subprocess
import os


def scan_todos(directory=".", max_results=10):
    """Grep for TODO/FIXME/HACK/XXX in directory.
    Returns dict with total count and sample matches."""
    excludes = [
        "--exclude-dir=.git",
        "--exclude-dir=node_modules",
        "--exclude-dir=__pycache__",
        "--exclude-dir=.venv",
        "--exclude-dir=venv",
        "--exclude-dir=.tox",
        "--exclude-dir=dist",
        "--exclude-dir=build",
        "--exclude=*.pyc",
        "--exclude=*.min.js",
    ]
    try:
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", "--include=*.js", "--include=*.ts",
             "--include=*.go", "--include=*.rs", "--include=*.java", "--include=*.rb",
             "--include=*.c", "--include=*.cpp", "--include=*.h", "--include=*.jsx",
             "--include=*.tsx", "--include=*.sh", "--include=*.yaml", "--include=*.yml",
             "--include=*.toml", "--include=*.md",
             "-E", r"(TODO|FIXME|HACK|XXX|BUG|OPTIMIZE)\b"]
            + excludes + [directory],
            capture_output=True, text=True, timeout=10
        )
        lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        total = len(lines)

        # Count by type
        by_type = {"TODO": 0, "FIXME": 0, "HACK": 0, "XXX": 0, "OTHER": 0}
        for line in lines:
            found = False
            for t in ["TODO", "FIXME", "HACK", "XXX"]:
                if t in line.upper():
                    by_type[t] += 1
                    found = True
                    break
            if not found:
                by_type["OTHER"] += 1

        # Sample matches
        samples = []
        for line in lines[:max_results]:
            # Shorten paths
            if ":" in line:
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    fpath = parts[0]
                    if len(fpath) > 30:
                        fpath = "..." + fpath[-27:]
                    samples.append(f"{fpath}:{parts[1]}: {parts[2][:60]}")
                else:
                    samples.append(line[:80])
            else:
                samples.append(line[:80])

        return {"total": total, "by_type": by_type, "samples": samples}

    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {"total": 0, "by_type": {}, "samples": []}


def format_todo_report(data):
    """Format scan results for speech bubble."""
    if data["total"] == 0:
        return "No TODOs found! Either your code is perfect\nor you're just really good at ignoring them."

    lines = [f"Found {data['total']} code markers:"]
    for t, count in data["by_type"].items():
        if count > 0:
            lines.append(f"  {t}: {count}")
    lines.append("")
    if data["samples"]:
        lines.append("Top matches:")
        for s in data["samples"][:5]:
            lines.append(f"  {s}")
    return "\n".join(lines)


def check_pending_prs():
    """Check for open PRs via gh CLI. Returns formatted string or None."""
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--state", "open", "--limit", "5",
             "--json", "number,title,author"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return None

        import json
        prs = json.loads(result.stdout)
        if not prs:
            return "No open PRs! Inbox zero energy."

        lines = [f"Open PRs ({len(prs)}):"]
        for pr in prs:
            author = pr.get("author", {}).get("login", "?")
            lines.append(f"  #{pr['number']} {pr['title'][:40]} ({author})")
        return "\n".join(lines)

    except FileNotFoundError:
        return "Install `gh` CLI to check PRs:\n  brew install gh"
    except (subprocess.TimeoutExpired, Exception):
        return None


def format_pr_report(text):
    """Pass-through for now."""
    return text if text else "Could not check PRs."
