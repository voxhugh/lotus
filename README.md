<div align="center">
  <h1>Lotus</h1>
  <p><strong>A personal knowledge archive</strong></p>
  <p>把好奇心留下来，把理解沉淀下来。</p>
  <p>
    <a href="https://voxhugh.github.io/lotus/">Explore the knowledge base ↗</a>
    &nbsp;·&nbsp;
    <a href="https://github.com/voxhugh/lotus/blob/main/MAINTENANCE.md">Maintainer notes</a>
  </p>
</div>

---

## About

Lotus is a living archive of technical notes: things learned, questions investigated, and details worth returning to.

The online documentation site brings the notes together in one place, with a shared navigation tree and full-text search.

## How it works

- **Independent topics** — each topic is maintained in its own Git branch.
- **One registry** — [`notes-branches.json`](notes-branches.json) defines which branches are published and how they appear on the site.
- **Automatic publishing** — GitHub Actions collects registered notes and publishes the site through GitHub Pages.

## Start here

**[Open Lotus →](https://voxhugh.github.io/lotus/)**

The topic list is generated from the registry during the site build, so the website—not a duplicated list in this README—is the current index of available notes.
