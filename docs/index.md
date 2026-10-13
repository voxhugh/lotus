# Lotus

> 个人技术笔记，记录知识、理解与实践。

Lotus 按技术主题组织笔记。每个主题仍由独立 Git 分支维护，网站构建时会自动汇集各分支中的 Markdown、图片和其他附件，在同一个站点内浏览与搜索。

<div class="grid cards" markdown>

-   **C++**

    ---

    语言基础、对象模型、内存布局与 STL。

    [浏览 C++ 笔记](cpp/index.md)

-   **Assembly**

    ---

    汇编与底层相关知识。

    [浏览汇编笔记](assembly/index.md)

-   **Linux**

    ---

    Linux 系统与开发相关知识。

    [浏览 Linux 笔记](linux/index.md)

-   **Python**

    ---

    Python 语言相关笔记。

    [浏览 Python 笔记](python/index.md)

-   **SQL**

    ---

    SQL 与数据库相关知识。

    [浏览 SQL 笔记](sql/index.md)

</div>

---

各主题分支独立维护，网站部署由 GitHub Actions 自动完成。修改主题分支后，通知工作流会触发主分支重新构建；每日也会执行一次兜底同步。
