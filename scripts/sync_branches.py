#!/usr/bin/env python3
"""Mirror each notes branch into docs/ before MkDocs builds the site."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
BRANCHES = {
    "cc": "cpp",
    "asm": "assembly",
    "lnx": "linux",
    "py": "python",
    "sql": "sql",
}
EXCLUDED_ROOT_FILES = {".gitignore", ".gitattributes", ".gitmodules", ".nojekyll"}
EXCLUDED_DIRS = {".github", ".git", "site"}
LINK_PATTERN = re.compile(r"(?P<prefix>\]\()(?P<url><[^>]+>|[^)\s]+)(?P<suffix>[^)]*\))")


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    )


def copy_branch(branch: str, destination: Path) -> None:
    ref = f"origin/{branch}"
    run(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"], capture=True)

    with tempfile.TemporaryDirectory(prefix=f"lotus-{branch}-") as temp_name:
        temp_root = Path(temp_name) / "content"
        temp_root.mkdir(parents=True)
        archive_path = Path(temp_name) / "branch.tar"
        with archive_path.open("wb") as archive:
            subprocess.run(
                ["git", "archive", "--format=tar", ref],
                cwd=ROOT,
                check=True,
                stdout=archive,
            )

        with tarfile.open(archive_path, "r:") as archive:
            for member in archive.getmembers():
                relative = PurePosixPath(member.name)
                if relative.is_absolute() or ".." in relative.parts:
                    raise RuntimeError(f"Unsafe path in {ref}: {member.name}")
                if not relative.parts:
                    continue
                if any(part in EXCLUDED_DIRS for part in relative.parts):
                    continue
                if len(relative.parts) == 1 and relative.name in EXCLUDED_ROOT_FILES:
                    continue

                target = temp_root.joinpath(*relative.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source = archive.extractfile(member)
                    if source is None:
                        continue
                    with source, target.open("wb") as output:
                        shutil.copyfileobj(source, output)
                elif member.issym() or member.islnk():
                    # Notes rarely need symlinks; skip them instead of copying a
                    # potentially unsafe link outside the documentation tree.
                    print(f"Warning: skipped link in {ref}: {member.name}", file=sys.stderr)

        readme = temp_root / "README.md"
        index = temp_root / "index.md"
        has_readme = readme.is_file()
        if has_readme and not index.exists():
            # Rewrite relative Markdown links that point at the root README
            # before renaming README.md to the section landing page index.md.
            for md_file in temp_root.rglob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue

                def rewrite(match: re.Match[str]) -> str:
                    raw_url = match.group("url")
                    if raw_url.startswith("<") or "://" in raw_url or raw_url.startswith(("#", "//", "mailto:")):
                        return match.group(0)
                    path_and_suffix = re.split(r"(?=[?#])", raw_url, maxsplit=1)
                    target_text = path_and_suffix[0]
                    suffix = raw_url[len(target_text):]
                    if not target_text:
                        return match.group(0)
                    target_path = (md_file.parent / target_text).resolve()
                    if target_path != readme.resolve():
                        return match.group(0)
                    new_target = Path(os.path.relpath(index, md_file.parent)).as_posix()
                    return f"{match.group('prefix')}{new_target}{suffix}{match.group('suffix')}"

                rewritten = LINK_PATTERN.sub(rewrite, content)
                if rewritten != content:
                    md_file.write_text(rewritten, encoding="utf-8")
            readme.rename(index)

        if not index.exists():
            # A few branches may contain topic files without a root README.
            # Generate a small landing page so homepage links never point to a
            # missing index; the rest of the files remain in the auto sidebar.
            title = {
                "cc": "C++",
                "asm": "Assembly",
                "lnx": "Linux",
                "py": "Python",
                "sql": "SQL",
            }.get(branch, branch)
            markdown_files = sorted(
                (p for p in temp_root.glob("*.md") if p.name.lower() not in {"readme.md", "index.md"}),
                key=lambda p: p.name.lower(),
            )
            if not markdown_files:
                markdown_files = sorted(
                    (p for p in temp_root.rglob("*.md") if p.name.lower() not in {"readme.md", "index.md"}),
                    key=lambda p: p.as_posix().lower(),
                )[:50]
            lines = [f"# {title}", "", "This topic branch does not have a root README. Select a note below or use the sidebar.", ""]
            if markdown_files:
                lines.extend(["## Notes", ""])
                for note in markdown_files:
                    rel = note.relative_to(temp_root).as_posix()
                    label = note.stem.replace("_", " ").replace("-", " ")
                    lines.append(f"- [{label}]({rel})")
                lines.append("")
            index.write_text("\n".join(lines), encoding="utf-8")

        # Replace only this topic's generated mirror; preserve docs/index.md
        # and all other topic directories.
        if destination.exists():
            shutil.rmtree(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(temp_root, destination)

    print(f"Synced {ref} -> docs/{destination.name}/")


def main() -> int:
    if not (ROOT / "mkdocs.yml").is_file():
        print("Run this script from the Lotus repository.", file=sys.stderr)
        return 2

    # The workflow explicitly fetches all branches first. Keep this script
    # read-only with respect to Git refs; it only updates generated docs/ files.
    for branch, folder in BRANCHES.items():
        copy_branch(branch, DOCS / folder)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
