# Lotus · 个人维护手册

> 这份文档记录仓库如何运作、日常如何维护。正常阅读笔记时不需要看这里。

## 维护原则

- **笔记源文件只留在主题分支。** `cc`、`asm`、`lnx`、`py`、`sql` 等分支独立维护。
- **主题清单只有一个事实来源。** `notes-branches.json` 决定哪些分支被发布、站点目录名、展示标题和简介。不要再在工作流里手写主题名单。
- **生成内容不提交。** `generated_docs/` 和 `site/` 都是临时产物，由构建流程创建。
- **入口保持薄。** 根目录 `README.md` 只介绍项目并链接站点；动态主题列表由构建脚本生成到网站首页。

## 日常更新笔记

例如更新 C++：

```bash
git switch cc
# 编辑笔记
git add .
git commit -m "Update C++ notes"
git push origin cc
```

主题分支中的 `.github/workflows/lotus-docs-notify.yml` 会检查该分支是否登记在 `notes-branches.json`。已登记的分支会发出 `notes-updated` 事件，主分支的部署工作流随后重新抓取全部主题、汇集文件、构建并发布网站。无需把笔记复制到 `main`。

发布不是即时完成的。到仓库 Actions 页面查看 `Deploy Lotus Docs` 的构建和部署状态。每日定时构建是兜底，并非日常更新的主要路径。

## 新增主题

以 `rust` 为例：

1. 创建并推送独立的 `rust` 笔记分支。新主题建议从空分支开始，避免把 `main` 的站点配置误带进笔记分支。
2. 在 `notes-branches.json` 的 `topics` 数组增加一个对象：

   ```json
   {
     "branch": "rust",
     "directory": "rust",
     "title": "Rust",
     "description": "Rust 语言与生态笔记。"
   }
   ```

3. 提交并推送 `main` 的清单修改。
4. 在干净的 `main` 工作区运行：

   ```bash
   python scripts/install_branch_triggers.py
   ```

   脚本会根据清单为所有主题分支安装或更新通知工作流。执行前，先确认没有未提交改动；脚本会切换分支、提交工作流并推送。
5. 检查 Actions 和网站。新主题的首页、目录与同步目标由清单自动生成，不需要改 `mkdocs.yml`、`sync_branches.py` 或首页源码。

`branch` 是实际 Git 分支名；`directory` 是网站 URL 下的目录名，必须是唯一的单层目录名称；`title` 和 `description` 用于展示。

## 删除或改名主题

- 从 `notes-branches.json` 删除对应对象后推送 `main`，下次构建就不会再发布这个主题。
- 删除清单记录不会删除 Git 远端分支。确认不再需要历史笔记后，再单独删除远端分支。
- 分支改名时，先在 GitHub 完成分支改名，再更新清单并重新运行 `install_branch_triggers.py`。检查工作流后再删除旧分支引用。

## 文件地图

| 路径 | 用途 |
|---|---|
| `README.md` | 面向仓库访问者的轻量入口 |
| `MAINTENANCE.md` | 本维护手册 |
| `notes-branches.json` | 唯一主题注册表 |
| `mkdocs.yml` | 网站主题、导航功能和 Markdown 扩展 |
| `site-assets/lotus.css` | 网站视觉样式；构建时复制到生成目录 |
| `scripts/sync_branches.py` | 汇集主题分支、生成首页、处理根 README 与资源 |
| `scripts/install_branch_triggers.py` | 为登记的分支安装/更新通知工作流 |
| `.github/workflows/deploy.yml` | 构建、上传并发布 GitHub Pages |
| `.github/workflows/lotus-docs-notify.yml` | 放在主题分支中的轻量更新通知器 |
| `generated_docs/` | 构建时自动生成的 MkDocs 输入，不手改、不提交 |
| `site/` | MkDocs 输出目录，不手改、不提交 |
| `github-profile/README.md` | 单独的 GitHub 个人主页 README 模板，不属于 `lotus` 构建输入 |

## 本地预览与验证

在仓库根目录安装主题依赖后运行：

```bash
python -m pip install mkdocs-material
python scripts/sync_branches.py
mkdocs serve
```

本地预览地址通常是 `http://127.0.0.1:8000/`。同步脚本依赖 Git 中可解析的 `origin/<branch>` 引用；先执行 `git fetch origin --prune`。

发布前可以检查：

```bash
python -m json.tool notes-branches.json
python -m py_compile scripts/sync_branches.py scripts/install_branch_triggers.py
python scripts/sync_branches.py
mkdocs build --strict
```

## 故障排查

- **推送主题分支后网站没有更新：** 检查该分支是否存在通知工作流；检查名称是否在 `notes-branches.json` 中；查看对应分支的 Actions 日志。
- **通知步骤返回 403：** 检查仓库 `Settings → Actions → General → Workflow permissions`，仓库/组织策略需允许通知工作流使用 `GITHUB_TOKEN` 发出 repository dispatch。
- **构建找不到分支：** 检查 `notes-branches.json` 的拼写，并确认远端分支存在。
- **图片或相对链接失效：** 保持主题分支的相对目录结构；尽量使用相对 Markdown 链接。同步脚本会保留普通文件和图片；符号链接会被跳过。
- **导航顺序不符合预期：** 先检查注册表顺序和各分支的 `README.md` / `index.md`，再检查 MkDocs 生成日志。
- **样式没有加载：** 确认 `site-assets/lotus.css` 存在，且同步脚本把它复制到了 `generated_docs/stylesheets/lotus.css`。

## 一次性打扫清单

在确认文件已经合并到此版本后，检查 `main`：

- 删除旧版部署说明 `SETUP-PHASE2.md`，以本文件 `MAINTENANCE.md` 为准，避免两份指引分叉。
- 删除打包时的临时说明 `README-PACKAGE.md`（若存在；它不是应用或构建输入）。
- 当前仓库没有 `.gitignore`，只有 `.gitignore.fragment`；Git 不会自动将后者作为忽略规则。应用美化补丁时，先以片段内容创建真正的 `.gitignore`，再补入 `generated_docs/`、`site/`、`__pycache__/`、`*.py[cod]` 等规则。核对内容保留后，才删除 `.gitignore.fragment`。如果将来仓库已经存在 `.gitignore`，则应合并规则，不要覆盖。
- 从 Git 索引中删除已经跟踪的 Python 缓存：`git rm -r --ignore-unmatch scripts/__pycache__`。仅添加忽略规则不能取消已跟踪文件的版本控制。
- 如果仍有旧版 `docs/index.md`，且 `docs/` 没有其他需要保留的源文档，可删除旧 `docs/`。当前 `mkdocs.yml` 使用 `docs_dir: generated_docs`，它不再读取旧目录。
- 不要删除 `notes-branches.json`、工作流、同步脚本或各主题分支中的图片/笔记。这些属于必要源文件。

执行清理前用 `git status --short` 和 `git ls-files` 核对范围；完成后检查 `git diff --stat` 与 Actions 构建结果。
