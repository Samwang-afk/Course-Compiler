# extract 协议

把一份 Document IR(`ir/documents/<src_id>.json`)转成 Knowledge IR 提案,
写入 `ir/proposals/<src_id>.json`,并把源状态推进为 `proposed`。

提案形状见 `schemas/knowledge-ir.schema.json`(每个条目 `status: "proposed"`)。

## 硬规则

1. **每条必须带 `sources`**(src_id + block id + ref),可追溯。
2. **不发明内容**。材料没有的就是没有;缺口是缺口,不是创作。
3. **稳定 id**:同一概念跨批次必须复用同一 id。提取前先读现有
   `ir/knowledge.json`,已存在同概念 → 复用其 id(内容可更新)。
   id 格式 `k_<英文slug>`,如 `k_python_async_await`。
4. **图片**:只有 brief 里 `vision: "yes"` 时才能基于图片内容描述;
   否则只用 `caption`/`ocr`,并在条目里保留 `visual_refs` 指向 figure 块。
   永远不假装看过图。

## 粒度规则(防过度简化)

- 一个条目 = **"可独立复习、含完整上下文"** 的知识单元。
  例:"牛顿第二定律"条目应含公式 + 适用条件 + 例证,而不是单拆一个 F=ma。
- **禁止原子碎片**:不要一条只写一个公式或一个孤立定义。
- **禁止章节倾倒**:不要整章复制成一条。
- 疑问/存疑内容单独成 `question` 条目,不要混进概念。
- 公式条目(`formula`)必须带每个符号的含义与适用条件。

## 原文保真

每条目写 `context`:2-6 句直接从材料摘录的原文(保真,不改写),
用于笔记中的折叠引用块。没有合适原文就留空字符串。

## 提取类型

| type | 用途 |
|---|---|
| concept | 概念/原理/机制 |
| formula | 公式/定理(含符号说明、适用条件) |
| example | 例证/案例/习题 |
| question | 疑问/存疑/知识缺口 |
| fact | 事实/数据/清单 |

## 输出

`ir/proposals/<src_id>.json`:
```json
{"version": 1, "src_id": "src_0001",
 "items": [ {"id": "k_...", "type": "concept", "title": "...",
             "summary": "...", "detail": "...", "context": "...",
             "sources": [{"src_id": "src_0001", "block": "b12", "ref": "p3"}],
             "tags": [], "links": [], "status": "proposed"} ]}
```
然后用脚本推进状态:
```bash
powershell -File <learning-kb>/scripts/run.ps1 mark_status.py --state <dir> --src src_0001 --status proposed
```
