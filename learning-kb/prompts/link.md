# link + moc 协议

## link(互链)

对 `ir/knowledge.json` 中每个条目:
1. 找出语义相关的其他条目(共享概念、前后置依赖、同一主题下的例子与概念);
2. 把相关条目 id 写入 `links` 数组(只写存在的 id);
3. 链路要双向:被引条目不强制回填,但 MOC 会补聚合层。
4. 不要过度链接:每条 0-5 个 links,无关不硬凑。

## 分组(主题聚合,防碎片化)

把条目聚合成**主题**(1-3 层):每个主题一篇笔记,内含多个相关条目。
- 一篇笔记 = 一个主题 = 多条条目的聚合页,不是一条目一笔记;
- 主题粒度对齐用户学习目标:过大拆、过小并;
- 每主题产出主题名 + 成员条目 id 列表,写入
  `ir/topics.json`:`[{"topic": "异步基础", "path": "异步编程/异步基础", "items": ["k_..."]}]`

## moc(索引)

基于 topics.json 生成:
1. `Start Here.md`(vault 根,用 templates/start_here.md);
2. 每个一级主题一个 MOC 页(templates/moc.md),列子主题与条目笔记的 wikilink;
3. MOC 之间互链。

## 编译(compile)

按 topics.json 逐篇生成笔记:
- 用 templates/note.md;frontmatter 填 tags / sources / updated;
- 每条条目渲染为正文小节:标题 + detail + 可折叠原文引用块(`<details>` 包裹 context);
- 外部条目额外套 templates/callout_external.md;uncertain/conflict 套
  templates/callout_unverified.md;
- 条目内与条目间用 `[[wikilink]]` 互链;来源引用放在笔记尾部"## 来源";
- 全部产物写入 `staging/`(相对 vault 的路径结构);
- 所有生成内容包在 `<!-- lkb-managed:start -->` … `<!-- lkb-managed:end -->`
  内;用户手写内容在区域外,增量更新时保留。

完成后:
```bash
powershell -File <learning-kb>/scripts/run.ps1 qa_check.py --state <dir>
```
qa 通过 → 进入 review 阶段。
