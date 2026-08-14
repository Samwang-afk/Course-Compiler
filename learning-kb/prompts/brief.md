# brief 协议

在触碰任何材料前,确认以下信息并持久化到 `.learning-kb/brief.json` 与 `BRIEF.md`。

## 必问(缺一不可)

1. **学习目标**(一句话,用户原话为准;可提供选项:备考复习 / 掌握某主题 / 面试准备 / 长期知识库 / 自定义)。
2. **主题范围**:科目/领域、层级、大纲(有就说,没有留空,永不猜测)。
3. **vault 路径**:用户指定的 Obsidian vault 绝对路径。若用户给了相对路径,基于当前工作目录解析并确认。
4. **外部知识档位**(三档,默认 official):
   - `strict` — 只用用户材料,缺口标"待补",永不联网;
   - `official` — 仅官方/权威来源补缺口(官方文档、官方 syllabus、教科书、权威机构),每条标 URL + External callout;
   - `yolo` — 自动补重要缺口,任意来源,每条标来源 + trust 分级,进 Review Queue 可复核。
5. **视觉能力**:检测当前模型能否实际看到图片。不能就写 `vision: "no"`,并告诉用户"我无法看图,图片将保留原图 + OCR + 标注未验证"。绝不假装看过图。

## 选问(用户愿答才记)

- 笔记语言(默认跟随材料语言)
- 深度偏好(条目粗细、笔记长度)
- 增量还是首建

## 持久化

```bash
powershell -File <learning-kb>/scripts/run.ps1 <无对应脚本>  # brief 由你直接写文件
```

brief 文件由 **agent 直接写 JSON**,形状见 `schemas/brief.schema.json`:

```json
{
  "version": 1,
  "vault_path": "D:/obsidian/my-vault",
  "state_dir": "D:/obsidian/my-vault/.learning-kb",
  "goal": "掌握 Python 异步编程",
  "topic_scope": "",
  "language": "zh",
  "external_policy": "official",
  "vision": "yes",
  "notes": ""
}
```

同时渲染一份人类可读的 `BRIEF.md`(vault、目标、档位、视觉、注意事项)。
之后把 `status.json` 的 `stage` 置为 `ingest`。
