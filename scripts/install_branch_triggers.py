#!/usr/bin/env python3
"""Install the tiny docs-notification workflow on each notes branch."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRANCHES = ("cc", "asm", "lnx", "py", "sql")
WORKFLOW_REL = Path(".github/workflows/lotus-docs-notify.yml")


def git(*args: str, capture: bool = False) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else ""


def main() -> int:
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

    workflow_contents = source.read_bytes()
    git("fetch", "origin", "--prune")

    # Validate every local branch before changing any branch, so a mismatch
    # cannot leave a partially installed set of notifier workflows.
    remote_shas: dict[str, str] = {}
    for branch in BRANCHES:
        remote_shas[branch] = git("rev-parse", f"origin/{branch}", capture=True)
        local_exists = subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
            cwd=ROOT,
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
        for branch in BRANCHES:
            local_exists = subprocess.run(
                ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
                cwd=ROOT,
            ).returncode == 0
            if local_exists:
                git("switch", branch)
            else:
                git("switch", "--track", "-c", branch, f"origin/{branch}")

            destination = ROOT / WORKFLOW_REL
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(workflow_contents)
            changed = subprocess.run(
                ["git", "diff", "--quiet", "--", str(WORKFLOW_REL)], cwd=ROOT
            ).returncode != 0
            staged_changed = subprocess.run(
                ["git", "diff", "--cached", "--quiet", "--", str(WORKFLOW_REL)], cwd=ROOT
            ).returncode != 0
            if changed or staged_changed or subprocess.run(
                ["git", "ls-files", "--error-unmatch", str(WORKFLOW_REL)],
                cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            ).returncode != 0:
                git("add", str(WORKFLOW_REL))
                staged = git("diff", "--cached", "--name-only", capture=True)
                if staged:
                    git("commit", "-m", "Add automatic documentation rebuild trigger")
                    git("push", "origin", branch)
                    completed.append(branch)
                    print(f"Installed notifier on {branch}")
                else:
                    print(f"Notifier already up to date on {branch}")
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
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
