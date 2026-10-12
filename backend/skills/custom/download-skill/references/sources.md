# 第三方技能来源与下载链接

## 去哪里找

按顺序搜索，找到符合用户要求且能核实来源的候选即可停止；不要因为某个目录站收录了技能就认定它可安装。

1. [Skills Directory / skills.sh](https://www.skills.sh/)：跨 Agent 的技能目录，可按技能名、任务或作者搜索。搜索示例：`site:skills.sh <任务关键词> skill`。
2. [SkillsMP](https://skillsmp.com/)：按任务、类别和作者查找公开技能；技能详情通常提供 GitHub 来源。搜索示例：`site:skillsmp.com <任务关键词> SKILL.md`。
3. [Skills Directory](https://www.skillsdirectory.com/)：按用途搜索技能并查看详情。搜索示例：`site:skillsdirectory.com/skills <任务关键词>`。
4. [ClawHub](https://clawhub.ai/)：OpenClaw 的技能目录，可补充查找相关技能。只在能找到完整技能目录的 GitHub 来源或直接压缩包链接、且结构适合本项目时安装；ClawHub 的页面或安装命令本身不能传给 `install_skill`。
5. [GitHub](https://github.com/)：目录站未找到时直接搜索 `<任务关键词> SKILL.md`，或查看作者的技能仓库，例如 [Anthropic 的公开技能仓库](https://github.com/anthropics/skills)。以仓库中的实际文件为准。

先用 `web_search` 查这些域名和任务关键词，再用 `fetch_url` 查看候选页面；若页面依赖脚本而无法读取，改查它指向的 GitHub 来源。搜索结果和目录站可能滞后，安装前以仓库当前分支的真实目录结构为准，不根据技能名自行拼出 `skills/<名字>`。仓库里的技能可能直接位于根目录，也可能位于 `skills/` 下。

[Agent Skills 规范](https://agentskills.io/)用于核对包结构，不是技能下载网站。

## 哪种链接能安装

1. GitHub 上的具体技能目录：`https://github.com/<作者>/<仓库>/tree/<分支>/<目录路径>`。目录本身要包含 `SKILL.md`。当前工具按 `tree/` 后第一个路径段识别分支，因此分支名中带 `/` 的链接暂不适用。
2. 直接下载单技能压缩包的 HTTP/HTTPS 链接：支持 `.skill`、`.zip`、`.7z`、`.tar`、`.tar.gz`、`.tar.bz2`、`.tar.xz`、`.tgz`、`.tbz2`、`.txz`。压缩包中应恰好有一个技能目录。

不要传技能展示页、GitHub 仓库首页、`blob/.../SKILL.md` 页面或 `raw/.../SKILL.md` 文件地址；这些不是当前工具接受的完整技能包来源。

## 调用和报错

先用 `tool_search` 找到 `install_skill` 的参数定义，再用 `url` 传入上述链接。工具会下载、检查并安装到配置指定的 `public` 分类；返回 `name`、`description`、`path`、`source_url`。

若报“GitHub 目录不是技能包”，先核对 `tree/` 后面的实际目录；报错可能附带仓库中找到的同名目录。若报“已存在同名技能”，不要换个名字重装，应把冲突告诉用户。若下载或校验失败，不要声称安装成功。
