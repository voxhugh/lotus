# Lotus Phase 2: unify all note branches into MkDocs

This overlay keeps the current branch layout (`cc`, `asm`, `lnx`, `py`, `sql`) and mirrors each branch into the deployed site during every build. Markdown files, relative images, and other tracked attachments are copied. The root `README.md` from each topic branch becomes that topic's `index.md`.

## Install

1. Use a local clone of `voxhugh/lotus`; make sure `main` is the checked-out branch and the working tree is clean. Back up anything uncommitted first.
2. Copy/merge the contents of this package into the repository root, preserving paths. Review `README.md`, `mkdocs.yml`, `docs/index.md`, `scripts/`, and `.github/workflows/`.
3. Commit and push the main-branch files (do not replace your existing `.gitignore`; this package intentionally does not provide one):

   ```bash
   git add README.md mkdocs.yml docs scripts .github/workflows/deploy.yml .github/workflows/lotus-docs-notify.yml SETUP-PHASE2.md
   git commit -m "Integrate notes branches into Lotus docs site"
   git push origin main
   ```

4. Install the branch notification workflow from a clean main working tree:

   ```bash
   python scripts/install_branch_triggers.py
   ```

   This script adds `.github/workflows/lotus-docs-notify.yml` to `cc`, `asm`, `lnx`, `py`, and `sql`, commits and pushes that workflow to each branch, and then switches back to `main`. It refuses to proceed if the main working tree is dirty or if a local topic branch differs from its remote tip. Run it from a clean clone if you have locally diverged branches.

5. In GitHub, confirm **Settings → Pages → Build and deployment → Source** is set to **GitHub Actions**. In **Settings → Actions → General**, make sure workflows have permission to run and that the default `GITHUB_TOKEN` can have the requested per-workflow permissions. The notifier specifically needs `contents: write` to emit `repository_dispatch`; the deployment workflow declares only `contents: read`, `pages: write`, and `id-token: write`.

6. Open **Actions → Deploy Lotus Docs** and inspect the build. The site should be published at `https://voxhugh.github.io/lotus/` after the run succeeds.

## Update behavior

- A push to `main` builds and deploys the website.
- A push to any note branch runs that branch's notifier, which sends a `notes-updated` repository-dispatch event. The build/deploy runs from the default branch (`main`) and fetches the latest tips of all note branches.
- A daily scheduled build is included as a fallback; you can also run **Deploy Lotus Docs → Run workflow** manually.

## Important notes

- The script does not push or rewrite the note contents. It only generates `docs/{cpp,assembly,linux,python,sql}/` during the Actions run; these generated mirrors are not committed to `main`.
- The sync excludes GitHub workflow metadata and root Git metadata files from the published documentation. Symlinks in topic branches are skipped for safety.
- `mkdocs build` is intentionally not run with `--strict` for the first rollout, so any pre-existing broken local links show as warnings instead of immediately blocking deployment. Review the Actions log and fix broken links later.
- Internal relative links and image paths are preserved in their branch-relative layout. Root README links are rewritten when that README becomes `index.md`. Links that hard-code external `github.com/.../blob/<branch>/...` URLs will continue to open GitHub rather than the site.
