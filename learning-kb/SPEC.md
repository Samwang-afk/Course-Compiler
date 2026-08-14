# SPEC: learning-kb — 多格式学习材料 → Obsidian 深度知识库

日期: 2026-08-13
状态: 已确认(设计三节全部通过用户审阅)

## 1. 目标

把各种格式的学习材料(文档 / 音视频 / 网页 / 聊天记录与表格)自动整合为
**深度重构的 Obsidian 知识库**:概念提取、跨源去重合并、wikilink 互链、
自动 MOC 索引,支持批量首建 + 持续增量。

## 2. 已确认需求(头脑风暴结论)

| 维度 | 决定 |
|---|---|
| 输入格式 | 文档(PDF/PPTX/DOCX/EPUB/TXT/MD)、音频/视频、网页/链接、聊天记录/表格 |
| 产出形态 | 深度重构知识库(非归档、非原子碎片) |
| 架构 | Agent + 轻脚本混合;确定性工作脚本化,理解工作由 agent 协议完成 |
| 转写 | 本地 whisper |
| 使用模式 | 批量首建 + 持续增量,两者都要 |
| 库位置 | 每次任务指定 vault 路径 |
| 外部知识 | 三档:Strict / Official Source / YOLO(默认 Official Source) |
| 视觉 | 自动检测模型视觉能力,绝不假装看过图 |
| 组织方式 | 方案 B:主 skill 路由器 + 阶段子 skill(family 模式) |

## 3. 管线

```
brief → ingest → parse → extract → merge → link → moc → qa → review → commit
```

| 阶段 | 执行者 | 说明 |
|---|---|---|
| brief | 主 skill (LLM) | 确认 vault、外部档位、视觉能力 → 写 brief.json + BRIEF.md |
| ingest | kb-ingest (脚本+LLM) | 各格式 → 归一 markdown;sha256 去重;登记 sources.json |
| parse | 脚本 parse_ir.py | markdown → Document IR(块 + 来源定位 + 资产) |
| extract | kb-extract (LLM) | Document IR → Knowledge IR proposal(粗粒度条目,禁原子碎片) |
| merge | kb-link (LLM) | 跨源去重合并;冲突双保留;存疑进 Review Queue |
| link | kb-link (LLM+脚本) | 条目间 wikilink 互链 |
| moc | kb-link (脚本+LLM) | 主题 MOC + Start Here |
| qa | 脚本 qa_check.py | wikilink/资产/重名/引用校验 |
| review | 主 skill (LLM) | 批量不确定项,每条带"保持未知"选项 |
| commit | 脚本 commit.py | staging → vault,manifest + 备份 + 回滚 |

## 4. 粒度控制(防过度简化)

1. **条目粒度规则**:一个知识条目 = "可独立复习、含完整上下文"的单元。
   禁止拆成原子碎片。宁可大而完整。
2. **笔记聚合**:编译成篇按主题聚合,一篇笔记含多个相关条目;
   不是一个条目一篇笔记。
3. **原文保真**:每条条目附可折叠原文摘录引用块。
4. **抽审**:review 阶段随机抽 3 条条目让用户校准粒度。

## 5. 状态目录 `.learning-kb/`

默认在 vault 根下;`--state <dir>` 可覆盖。断点续行:任何 agent 读
`status.json` + `BRIEF.md` 即可接手,不依赖对话历史。

```
.learning-kb/
├── BRIEF.md / brief.json       # 目标、外部档位、视觉能力
├── status.json                 # 管线阶段 + 每源进度
├── sources.json                # 来源登记表
├── sources/<sha[:12]>.<ext>    # 原文件(内容寻址,永不修改)
├── extracted/<src_id>.md       # 归一 markdown
├── assets/<src_id>/…           # 图片等资产
├── ir/
│   ├── documents/<src_id>.json # Document IR
│   ├── proposals/<src_id>.json # extract 提案
│   └── knowledge.json          # 合并后 Knowledge IR
├── review.json                 # Review Queue
├── runs/<run_id>.json          # 批次 manifest
├── runs/backups/<run_id>/      # commit 前备份
└── staging/                    # 编译产物(commit 前)
```

## 6. Skill 划分

| Skill | 目录 | 职责 |
|---|---|---|
| `learning-kb` | skills/learning-kb | 主路由器:brief / 状态 / review / commit 编排;共享 schemas、scripts、templates |
| `kb-ingest` | skills/kb-ingest | 收材料协议(脚本调用约定、异常处置) |
| `kb-extract` | skills/kb-extract | 提取协议(粒度、来源、视觉、三档外部策略) |
| `kb-link` | skills/kb-link | merge + link + moc 协议 |

子 skill 通过相对路径 `../learning-kb/{scripts,schemas,templates}` 引用共享件。

## 7. 脚本清单(scripts/,全部确定性、零理解)

| 脚本 | 依赖 | 作用 |
|---|---|---|
| transcribe.py | whisper + ffmpeg | 音视频 → 带时间戳转写 markdown,断点续转 |
| fetch_url.py | requests + bs4 | 网页 → 干净 markdown |
| pdf2md.py | pymupdf | PDF → markdown + 图片资产 |
| docx2md.py | python-docx | DOCX → markdown |
| pptx2md.py | python-pptx | PPTX → markdown(含备注) |
| epub2md.py | ebooklib | EPUB → 按章 markdown |
| chat2md.py | 无 | 聊天导出 / CSV → markdown 表格 |
| parse_ir.py | 无 | markdown → Document IR |
| qa_check.py | 无 | staging 校验 |
| commit.py | 无 | 提交 / 状态 / 回滚 |
| common.py | 无 | 状态读写、源登记共享逻辑 |
| run.ps1 | uv | 入口:自动建 venv 装依赖后执行脚本 |
| setup.ps1 | uv | 建 venv + 安装 requirements.txt |

运行约定:所有脚本经 `powershell -File scripts/run.ps1 <脚本> <参数>` 调用;
缺依赖时 run.ps1 自动引导安装。脚本只做确定性转换,不做任何理解。

## 8. 增量与幂等

- 内容寻址存储,重复投递零变化(标记 duplicate)。
- 知识条目稳定 id,同概念跨批次复用;更新走 NEW/UPDATE/DUPLICATE/CONFLICT。
- 新增材料只影响其覆盖的条目与笔记,无关笔记不动。
- 生成笔记用 managed 区域包裹;区域外用户手写内容在增量更新时保留。
- 每次 commit 有 run manifest;rollback 回退;中断自动检测恢复。

## 9. 外部知识三档

| 档位 | 行为 |
|---|---|
| Strict | 只用用户材料,缺口标"待补"进 Review Queue,永不联网 |
| Official Source | 仅官方/权威来源补(官方文档、syllabus、教科书),每条标 URL + External callout |
| YOLO | 自动补重要缺口,任意来源,每条标来源 + trust 分级,可复核 |

默认 Official Source。

## 10. 视觉规则

- brief 阶段检测当前模型能否看图。
- 能:图 → 文字描述 + 保留原图;不能:OCR + 保留原图 + 标注"未视觉验证"。
- 永远不假装看过图;存疑视觉进 Review Queue。

## 11. 验收标准(端到端)

用样例材料(1 短音频 + 1 网页 + 1 PDF,主题一致)跑通 brief → commit,
断言:
1. vault 出现按主题聚合的笔记 + Start Here + MOC;
2. wikilink 互链存在且 qa_check 通过;
3. 重复投递同一文件零变化;
4. 回滚可用。
