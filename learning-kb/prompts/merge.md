# merge 协议(跨源去重合并)

把 `ir/proposals/*.json` 合并进 `ir/knowledge.json`。
每个提案条目相对现有知识库判定:

- **NEW** → `status: "accepted"`,直接入库;
- **UPDATE** → 内容有实质新增/修正,合并 sources 与内容,`status: "updated"`;
- **DUPLICATE** → 与已有条目同义,把 sources 并入已有条目,丢弃新条目;
- **CONFLICT** → 两个来源对同一概念有真矛盾:**两边都保留**(各一条目,
  `status: "conflict"`,在 detail 里注明对方主张),绝不替用户选边;
- **UNCERTAIN** → 疑似同一概念但没把握 → 保留为独立条目
  `status: "uncertain"`,写 `merge_notes` 说明疑点,进 Review Queue。

## 判定准则

- 字符串相似 ≠ 概念同一。以**语义**为准,拿不准就 UNCERTAIN,绝不悄悄合并。
- 等价公式形式(如 F=ma 与 a=F/m)不是冲突,是同一概念不同写法。
- 冲突只判"真矛盾"(互相否定),表述侧重不同不算。
- 外部知识条目(external 非空)不得改写材料条目,只能补充。

## 输出

更新后的 `ir/knowledge.json`(全量重写),然后:
```bash
powershell -File <learning-kb>/scripts/run.ps1 mark_status.py --state <dir> --src <每个已合并源> --status merged --stage link
```
UNCERTAIN / CONFLICT 条目登记进 `review.json`(见 review 协议)。
