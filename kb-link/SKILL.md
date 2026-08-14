# SKILL: kb-link(合并 + 互链 + 编译)

把 Knowledge IR 提案合并、互链、按主题聚合成 Obsidian 笔记。
由 `learning-kb` 主 skill 路由。纯理解协议;模板与校验脚本共享自
`../learning-kb/`。

协议分三步,详见:
- 合并:`../learning-kb/prompts/merge.md`
- 互链/MOC/编译:`../learning-kb/prompts/link.md`
- review 登记:`../learning-kb/prompts/review.md`

## 三步要点

### 1. merge(跨源去重)

提案逐个判定 NEW / UPDATE / DUPLICATE / CONFLICT / UNCERTAIN:
- 语义同一是合并依据,字符串相似不是;拿不准走 UNCERTAIN 并写 merge_notes;
- 真矛盾双保留(status conflict),绝不替用户选边;
- 结果全量写回 `ir/knowledge.json`;CONFLICT/UNCERTAIN 登记 review.json。

### 2. link + 分组

- 条目间语义相关 → 填 links(0-5 个,不硬凑);
- 条目聚合为主题(1-3 层)→ 写 `ir/topics.json`:
  `[{"topic": "主题名", "path": "目录路径", "items": ["k_..."]}]`;
- 一篇笔记 = 一个主题 = 多条目聚合页;**禁止一条目一笔记**。

### 3. 编译 staging

按 topics.json 生成笔记:
- 模板:`../learning-kb/templates/note.md`(frontmatter + managed 区域);
- 每条目小节:标题 + detail + `<details>` 折叠原文引用(context);
- external 条目套 `callout_external.md`,uncertain/conflict 套 `callout_unverified.md`;
- wikilink 互链;尾部"## 来源"列 source 定位;
- `Start Here.md` 用 `templates/start_here.md`;每主题一个 MOC(`templates/moc.md`);
- 全部写入 `staging/`,路径即 vault 内路径;
- 生成内容包在 `<!-- lkb-managed:start -->` / `<!-- lkb-managed:end -->` 内,
  区域外内容留给用户、增量时保留。

## 校验与交回

```bash
powershell -File ../learning-kb/scripts/run.ps1 qa_check.py --state <dir>
```
qa 通过 → 交回主 skill 进入 review/commit。
