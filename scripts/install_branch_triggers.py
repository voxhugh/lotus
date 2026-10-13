#!/usr/bin/env python3
"""Install/update the generic site-rebuild notifier in every registered topic branch."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "notes-branches.json"
WORKFLOW_REL = Path(".github/workflows/lotus-docs-notify.yml")


def git(*args: str, capture: bool = False) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else ""


def registered_branches() -> list[str]:
    data: Any = json.loads(MANIFEST.read_text(encoding="utf-8"))
    topics = data.get("topics") if isinstance(data, dict) else None
    if not isinstance(topics, list) or not topics:
        raise RuntimeError("notes-branches.json must contain a non-empty 'topics' array")
    branches = [item.get("branch") for item in topics if isinstance(item, dict)]
    if len(branches) != len(topics) or any(not isinstance(b, str) or not b.strip() for b in branches):
        raise RuntimeError("Every topic entry must have a non-empty branch")
    if len(set(branches)) != len(branches):
        raise RuntimeError("Duplicate branch names in notes-branches.json")
    if "main" in branches:
        raise RuntimeError("The main portal branch must not be listed as a topic")
    return branches


def main() -> int:
    if not MANIFEST.is_file():
        print(f"Missing branch registry: {MANIFEST}", file=sys.stderr)
        return 2
    source = ROOT / WORKFLOW_REL
    if not source.is_file():
        print(f"Missing workflow file: {source}", file=sys.stderr)
        return 2

    current = git("branch", "--show-current", capture=True)
    if current != "main":
        print(f"Please run this on branch 'main' (currently on '{current}').", file=sys.stderr)
        return 2
    if git("status", "--porcelain", capture=True):
        print("Working tree is not clean. Commit/push main and start again.", file=sys.stderr)
        return 2

    branches = registered_branches()
    workflow_contents = source.read_bytes()
    git("fetch", "origin", "--prune")

    remote_shas: dict[str, str] = {}
    for branch in branches:
        remote_shas[branch] = git("rev-parse", f"origin/{branch}", capture=True)
        local_exists = subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=ROOT
        ).returncode == 0
        if local_exists:
            local_sha = git("rev-parse", f"refs/heads/{branch}", capture=True)
            if local_sha != remote_shas[branch]:
                raise RuntimeError(
                    f"Local branch '{branch}' differs from origin/{branch}. "
                    "Use a clean clone (or align the branch manually) to avoid pushing unrelated commits."
                )

    completed: list[str] = []
    try:
        for branch in branches:
            local_exists = subprocess.run(
                ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=ROOT
            ).returncode == 0
            if local_exists:
                git("switch", branch)
            else:
                git("switch", "--track", "-c", branch, f"origin/{branch}")

            destination = ROOT / WORKFLOW_REL
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(workflow_contents)
            git("add", str(WORKFLOW_REL))
            staged = git("diff", "--cached", "--name-only", capture=True)
            if staged:
                git("commit", "-m", "Add or update automatic documentation rebuild trigger")
                git("push", "origin", branch)
                completed.append(branch)
                print(f"Updated notifier on {branch}")
            else:
                print(f"Notifier already up to date on {branch}")
    finally:
        git("switch", "main")

    print("Finished. Updated branches: " + (", ".join(completed) if completed else "none"))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"Git command failed with exit code {exc.returncode}.", file=sys.stderr)
        sys.exit(exc.returncode or 1)
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
