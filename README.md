# Course Compiler

> Course Compiler by samwangafk — 把各种格式的学习材料自动整合成深度重构的 Obsidian 知识库。

A skill family that turns learning materials in **any format** — documents
(PDF / PPTX / DOCX / EPUB / Markdown), audio & video, web pages, chat exports
& tables — into a **deeply-restructured Obsidian knowledge base**: concept
extraction, cross-source dedup & merge, wikilink interlinking, automatic MOC
indexes. Supports both one-shot bulk import and continuous incremental
updates.

```
brief → ingest → parse → extract → merge → link → moc → qa → review → commit
```

## 安装

把四个 skill 目录复制到你的 agent skills 目录(如 `~/.config/opencode/skills/`
或 `~/.claude/skills/`),保持兄弟目录关系(子 skill 通过 `../learning-kb/`
引用共享件):

```
skills/
  learning-kb/    # 主 skill:路由器 + scripts + schemas + templates + prompts
  kb-ingest/      # 子 skill:收材料(格式转换、转写、抓取)
  kb-extract/     # 子 skill:知识提取(粒度、来源、视觉规则)
  kb-link/        # 子 skill:合并 + 互链 + MOC + 编译
```

首次运行脚本时自动安装依赖(Python 3.12+/uv、ffmpeg 需已装):

```
powershell -File learning-kb/scripts/setup.ps1
```

## 用法

对 agent 说:"把 D:\课程材料 整理进 D:\obsidian\vault,目标是备考复习"。

Agent 会走 brief 三问(目标 / 外部知识档位 Strict-Official-YOLO / 视觉能力),
然后自动完成管线,不确定项批量进 Review Queue(永远带"保持未知"选项),
用户手写内容(manged 区域外)在增量更新时保留。

## 核心保证

- **原文件永不修改**:内容寻址(sha256)存储,重复投递零变化。
- **全程可溯源**:每条知识带 来源+页/时间戳 引用;外部补充永远显式标记。
- **粒度控制**:条目"可独立复习但含完整上下文",笔记按主题聚合,不切碎片。
- **视觉诚实**:模型不能看图就绝不假装看过,图片保原图 + OCR + 标注。
- **增量安全**:只动受影响笔记;每次 commit 有 manifest + 备份,可回滚。
- **断点可续**:状态全在磁盘 `.learning-kb/`,任何 agent 可接手。

## 测试

```
uv pip install --python learning-kb/.venv/Scripts/python.exe -r learning-kb/scripts/requirements-dev.txt
learning-kb/.venv/Scripts/python.exe -m pytest learning-kb/tests
```

83 例:单元 + 转换器 + e2e 全管线 + 增量 + 压测(体量/unicode/损坏文件)。
仅压测:`-m stress`;PowerShell 冒烟:`-m powershell`。

## 仓库结构

```
Course-Compiler/
  README.md
  learning-kb/    SKILL.md  SPEC.md  schemas/  scripts/  templates/  prompts/  tests/
  kb-ingest/      SKILL.md
  kb-extract/     SKILL.md
  kb-link/        SKILL.md
```

## License

MIT
