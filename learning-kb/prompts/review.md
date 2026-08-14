# review 协议

批量呈现不确定项给用户,每条给出建议动作、备选,**永远带"保持未知"选项**。
管线绝不因单条卡住;用户不答复也能继续,未决项保持标记。

## 条目来源

`review.json` 累积以下类型(管线运行中自动产生):

| kind | 来源阶段 | 说明 |
|---|---|---|
| visual | parse/extract | 无法视觉验证的图片/图表 |
| merge | merge | UNCERTAIN 合并疑点 |
| conflict | merge | 真矛盾,需用户拍板 |
| gap | extract | 知识缺口(按外部档位处理) |
| placement | compile | 主题归属不确定的条目 |

形状:
```json
{"items": [{"id": "rv_001", "kind": "merge", "status": "open",
  "question": "k_a 与 k_b 是否同一概念?",
  "options": [{"id": "merge", "label": "合并", "effect": "..."},
              {"id": "keep", "label": "保持分开", "effect": "..."},
              {"id": "unknown", "label": "保持未知", "effect": "保留标注"}],
  "item_ref": "k_a", "resolution": null}]}
```

## 呈现方式

1. 每轮最多 30 条,编号列出:`(1) 问题 → 选项 a/b/c`;
2. 用户回复编号 + 选择,批量记录 `resolution` 并执行 effect;
3. 粒度抽审:随机抽 3 条知识条目展示完整内容,问"粒度是否合适",
   用户反馈用于后续 extract 校准。

## 外部档位在 review 中的行为

- `strict`:缺口全部标"待补",提示用户可自行补充;
- `official`:把重要缺口批量列出,问一次"是否允许官方来源补充?",
  同意后才做研究,每条带 URL;
- `yolo`:已自动补的条目列出供用户抽查撤销。

review 全部处理完(或用户跳过)后 → commit:
```bash
powershell -File <learning-kb>/scripts/run.ps1 commit.py --state <dir> commit
```
