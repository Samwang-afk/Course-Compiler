# SKILL: kb-extract(知识提取)

把 Document IR 逐源转成 Knowledge IR 提案。由 `learning-kb` 主 skill 路由。
本 skill 是纯理解协议,不写脚本;唯一执行的脚本是状态推进。

详细协议见 `../learning-kb/prompts/extract.md`(必读),要点:

## 输入输出

- 输入:`../<vault>/.learning-kb/ir/documents/<src_id>.json`
  (逐源处理,一次一个;大源分块)
- 输出:`ir/proposals/<src_id>.json`
  (形状:../learning-kb/schemas/knowledge-ir.schema.json,status 全 proposed)

## 粒度铁律

- 条目 = 可独立复习 + 含完整上下文;禁原子碎片;禁章节倾倒。
- 公式带符号含义与适用条件;疑问单独成 question 条目。
- 笔记聚合在 kb-link 阶段做,这里不要预判主题文件名。

## 稳定 id 与增量

提取前先读 `ir/knowledge.json`:同概念必须复用已有 id(可更新内容)。
新概念 id = `k_<slug>`。

## 来源与保真

- 每条带 sources(src_id + block + ref)。
- context 字段放 2-6 句原文摘录(保真),供笔记折叠引用。

## 视觉

brief 里 `vision: "yes"` 才可描述图片内容;否则只用 caption/ocr,
图片相关条目注明"未视觉验证"。绝不假装看过图。

## 状态推进

完成一个源后:
```bash
powershell -File ../learning-kb/scripts/run.ps1 mark_status.py --state <dir> --src <src_id> --status proposed
```
全部源完成后 stage → merge,交回主 skill。
