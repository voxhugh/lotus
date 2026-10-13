#!/usr/bin/env python3
"""Build a generated documentation tree from branches registered in JSON."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "generated_docs"
MANIFEST = ROOT / "notes-branches.json"
EXCLUDED_ROOT_FILES = {".gitignore", ".gitattributes", ".gitmodules", ".nojekyll"}
EXCLUDED_DIRS = {".github", ".git", "site", "generated_docs"}
LINK_PATTERN = re.compile(r"(?P<prefix>\]\()(?P<url><[^>]+>|[^)\s]+)(?P<suffix>[^)]*\))")


def git(*args: str, capture: bool = False) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else ""


def load_topics() -> list[dict[str, str]]:
    if not MANIFEST.is_file():
        raise RuntimeError(f"Missing branch registry: {MANIFEST}")
    data: Any = json.loads(MANIFEST.read_text(encoding="utf-8"))
    topics = data.get("topics") if isinstance(data, dict) else None
    if not isinstance(topics, list) or not topics:
        raise RuntimeError("notes-branches.json must contain a non-empty 'topics' array")

    seen_branches: set[str] = set()
    seen_dirs: set[str] = set()
    normalized: list[dict[str, str]] = []
    for item in topics:
        if not isinstance(item, dict):
            raise RuntimeError("Each topic entry must be an object")
        branch = item.get("branch", "")
        directory = item.get("directory", "")
        title = item.get("title", "")
        description = item.get("description", "")
        if not all(isinstance(v, str) and v.strip() for v in (branch, directory, title)):
            raise RuntimeError(f"Topic entry requires non-empty branch, directory and title: {item!r}")
        if branch.startswith("-") or "\x00" in branch:
            raise RuntimeError(f"Invalid branch name in registry: {branch!r}")
        # Keep topic directories as single safe path components.
        p = PurePosixPath(directory)
        if p.is_absolute() or len(p.parts) != 1 or p.parts[0] in {".", ".."}:
            raise RuntimeError(f"directory must be a single safe folder name: {directory!r}")
        if branch in seen_branches:
            raise RuntimeError(f"Duplicate branch in registry: {branch}")
        if directory in seen_dirs:
            raise RuntimeError(f"Duplicate directory in registry: {directory}")
        seen_branches.add(branch)
        seen_dirs.add(directory)
        normalized.append({
            "branch": branch,
            "directory": directory,
            "title": title.strip(),
            "description": description.strip() if isinstance(description, str) else "",
        })
    return normalized


def rewrite_root_readme_links(root: Path, readme: Path, index: Path) -> None:
    """Rewrite Markdown links resolving to the branch's root README as index.md."""
    for md_file in root.rglob("*.md"):
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


def make_homepage(topics: list[dict[str, str]]) -> str:
    lines = [
        "# Lotus", "", 
        "> 个人技术笔记，记录知识、理解与实践。", "",
        "Lotus 按技术主题组织笔记。各主题由独立 Git 分支维护，构建时自动汇集到同一个文档站。", "",
        '<div class="grid cards" markdown>', "",
    ]
    for topic in topics:
        title = topic["title"]
        description = topic["description"] or f"浏览 {title} 相关笔记。"
        directory = topic["directory"]
        lines.extend([
            f"-   **{title}**", "", "    ---", "", f"    {description}", "",
            f"    [浏览 {title} 笔记]({directory}/index.md)", "",
        ])
    lines.extend([
        "</div>", "", "---", "",
        "修改主题分支后，通知工作流会触发网站重新构建；每日定时构建提供兜底同步。", "",
    ])
    return "\n".join(lines)


def copy_branch(topic: dict[str, str], destination: Path) -> None:
    branch = topic["branch"]
    ref = f"origin/{branch}"
    git("rev-parse", "--verify", f"{ref}^{{commit}}", capture=True)

    with tempfile.TemporaryDirectory(prefix=f"lotus-{branch.replace('/', '-')}-") as temp_name:
        temp_root = Path(temp_name) / "content"
        temp_root.mkdir(parents=True)
        archive_path = Path(temp_name) / "branch.tar"
        with archive_path.open("wb") as archive_file:
            subprocess.run(
                ["git", "archive", "--format=tar", ref], cwd=ROOT,
                check=True, stdout=archive_file,
            )

        with tarfile.open(archive_path, "r:") as archive:
            for member in archive.getmembers():
                relative = PurePosixPath(member.name)
                if relative.is_absolute() or ".." in relative.parts:
                    raise RuntimeError(f"Unsafe path in {ref}: {member.name}")
                if not relative.parts or any(part in EXCLUDED_DIRS for part in relative.parts):
                    continue
                if len(relative.parts) == 1 and relative.name in EXCLUDED_ROOT_FILES:
                    continue
                target = temp_root.joinpath(*relative.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source = archive.extractfile(member)
                    if source is not None:
                        with source, target.open("wb") as output:
                            shutil.copyfileobj(source, output)
                elif member.issym() or member.islnk():
                    print(f"Warning: skipped link in {ref}: {member.name}", file=sys.stderr)

        readme = temp_root / "README.md"
        index = temp_root / "index.md"
        if readme.is_file() and not index.exists():
            rewrite_root_readme_links(temp_root, readme, index)
            readme.rename(index)

        if not index.exists():
            markdown_files = sorted(
                (p for p in temp_root.rglob("*.md") if p.name.lower() not in {"readme.md", "index.md"}),
                key=lambda p: p.as_posix().lower(),
            )[:100]
            lines = [
                f"# {topic['title']}", "",
                "本主题暂无根目录 README。可以从下面选择笔记，或使用左侧目录。", "",
            ]
            if markdown_files:
                lines.extend(["## 笔记", ""])
                for note in markdown_files:
                    rel = note.relative_to(temp_root).as_posix()
                    label = note.stem.replace("_", " ").replace("-", " ")
                    lines.append(f"- [{label}]({rel})")
                lines.append("")
            index.write_text("\n".join(lines), encoding="utf-8")

        if destination.exists():
            shutil.rmtree(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(temp_root, destination)

    print(f"Synced {ref} -> {destination.relative_to(ROOT).as_posix()}/")


def main() -> int:
    topics = load_topics()
    if not (ROOT / "mkdocs.yml").is_file():
        print("Run this script from the Lotus repository.", file=sys.stderr)
        return 2

    # Generated site sources live in a separate, disposable folder. A local build
    # will not rewrite committed portal source files.
    if DOCS.exists():
        shutil.rmtree(DOCS)
    DOCS.mkdir(parents=True)
    (DOCS / "index.md").write_text(make_homepage(topics), encoding="utf-8")

    for topic in topics:
        copy_branch(topic, DOCS / topic["directory"])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (subprocess.CalledProcessError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
