# Lotus Phase 2 (flexible branch registry)

This version removes the topic branch lists from the workflows and scripts. `notes-branches.json` is the single registry for branch names, site paths, titles, descriptions, generated homepage cards, branch syncing, and notifier installation.

## Install / upgrade

1. Make sure you are on `main` with a clean working tree. Download and extract this package, then merge its contents into the repository root.
2. Review these files: `README.md`, `mkdocs.yml`, `notes-branches.json`, `scripts/`, and `.github/workflows/`.
3. If you are replacing the earlier phase-2 package, `mkdocs.yml` now uses `docs_dir: generated_docs`. Old `docs/index.md` is no longer used; it may be removed from `main` to avoid confusion. Add `site/` and `generated_docs/` to your existing `.gitignore` if desired; do not replace an existing `.gitignore` wholesale.
4. Commit and push the main-branch files:

   ```bash
   git add README.md mkdocs.yml notes-branches.json scripts .github/workflows/deploy.yml .github/workflows/lotus-docs-notify.yml SETUP-PHASE2.md
   git commit -m "Make Lotus docs branch registry extensible"
   git push origin main
   ```

5. Install/update the generic notifier on all branches listed in `notes-branches.json`. Start with a clean local main working tree:

   ```bash
   python scripts/install_branch_triggers.py
   ```

   The script validates that local note branches match their remote tips before changing anything, commits only the notifier workflow, pushes each updated topic branch, and returns to `main`.

6. Ensure **Settings → Pages → Build and deployment → Source** is set to **GitHub Actions** and the Actions permissions allow `contents: write` for the notifier workflow.

## Updating existing notes

Edit, commit, and push a registered topic branch normally. Its notifier checks whether the branch appears in `notes-branches.json`; if it does, it emits a `notes-updated` repository-dispatch event. The `main` deploy workflow fetches the registered branch tips, generates `generated_docs/`, runs `mkdocs build`, and deploys Pages. A daily build is included as a fallback.

## Adding a new topic branch

1. Create and push the new notes branch first. For a clean new topic, use an orphan branch or create it from an existing topic branch and replace its note contents. Avoid basing a notes branch on `main`, because `main` contains portal scripts/config that are not notes.
2. On `main`, add one object to `notes-branches.json`, for example:

   ```json
   {
     "branch": "rust",
     "directory": "rust",
     "title": "Rust",
     "description": "Rust 语言与生态笔记。"
   }
   ```

   Put the new object into the existing `topics` array, including a comma after the preceding object. Keep `branch` unique and `directory` a unique single folder name. Push the updated manifest to `main`.
3. Run `python scripts/install_branch_triggers.py` from a clean `main` checkout. The script reads the manifest and installs/updates the notifier on all registered branches, including the new one. If the new branch did not inherit the notifier, this step adds it. The push that installs the notifier will then trigger a rebuild because the branch is now registered.

No edits are needed in `deploy.yml`, `sync_branches.py`, or the homepage for a new topic. The homepage, topic destination folder, and sync list are generated from `notes-branches.json`.

## Notes / limitations

- Only branches explicitly listed in `notes-branches.json` appear on the site. This avoids accidentally publishing temporary work branches.
- The sync script mirrors tracked branch files while excluding `.github`, Git metadata files, `site/`, and `generated_docs/`. Symlinks are skipped for safety.
- Each topic branch's root `README.md` becomes that topic's `index.md` when there is no existing `index.md`.
- Relative Markdown links and image paths retain their branch-relative layout. Hard-coded `github.com/.../blob/<branch>/...` links continue to open GitHub.
- The scripts do not commit the generated documentation; `generated_docs/` is produced on each build.
