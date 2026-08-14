# SKILL: learning-kb

> Course Compiler by samwangafk,开始前请确认此技能依赖大量子agent,需要多模态能力,token用量也会加大,确认?

把**各种格式的学习材料**(文档、音视频、网页、聊天记录/表格)自动整合成
**深度重构的 Obsidian 知识库**:概念提取、跨源去重合并、wikilink 互链、
自动 MOC 索引。支持批量首建 + 持续增量。

你是**主路由器**:负责 brief / 状态总览 / 阶段调度 / review / commit 编排。
理解类子阶段把协议交给子 skill(`kb-ingest` / `kb-extract` / `kb-link`),
通过 skill 工具加载它们。确定性工作全部走 `scripts/` 下的轻脚本,
状态在磁盘 `.learning-kb/` 上,任何 agent 断点可续。

---

## 何时使用

用户要求把学习材料(讲义、课程视频、文章链接、聊天记录、表格……)
整理进 Obsidian,且希望是**理解重构的知识库**而非逐文件摘要。
不做:文件格式转换、单纯汇总摘要。

## 管线总览

```
brief → ingest → parse → extract → merge → link/moc/compile → qa → review → commit
```

| 阶段 | 执行 | 入口 |
|---|---|---|
| brief | 你(LLM) | prompts/brief.md |
| ingest | 脚本 + 子 skill kb-ingest | scripts/*.py |
| parse | 脚本 | parse_ir.py --all |
| extract | 子 skill kb-extract | prompts/extract.md |
| merge | 子 skill kb-link | prompts/merge.md |
| link/moc/compile | 子 skill kb-link | prompts/link.md |
| qa | 脚本 | qa_check.py |
| review | 你(LLM) | prompts/review.md |
| commit | 脚本 | commit.py commit |

## 0. 接手状态(每次开工第一步)

```bash
powershell -File <本skill>/scripts/run.ps1 commit.py --state <state_dir> status
```

读 `BRIEF.md`、`status.json`、`sources.json`,从 `status.json` 的 `stage`
决定下一步。**没有 brief 就先做 brief,绝不跳过。**

## 1. brief(见 prompts/brief.md)

问清:学习目标 / 主题范围 / vault 路径 / 外部知识档位(strict|official|yolo,
默认 official)/ 视觉能力。写入 `brief.json` + `BRIEF.md`,stage → ingest。

## 2. ingest → parse(脚本化)

加载子 skill `kb-ingest` 获取调用约定,概括:

```bash
# 文档 / 音视频 / 网页 / 聊天表格,一次可多个:
powershell -File <本skill>/scripts/run.ps1 pdf2md.py   --state <dir> --input a.pdf
powershell -File <本skill>/scripts/run.ps1 transcribe.py --state <dir> --input a.mp4
powershell -File <本skill>/scripts/run.ps1 fetch_url.py --state <dir> --url https://...
# 全部转 Document IR:
powershell -File <本skill>/scripts/run.ps1 parse_ir.py --state <dir> --all
```

原文件永不修改(内容寻址复制);重复投递零变化;失败单文件不影响批次。

## 3. extract(加载 kb-extract)

逐源读 `ir/documents/<src_id>.json` → 写 `ir/proposals/<src_id>.json`。
粒度规则:**可独立复习但含完整上下文的知识单元,禁原子碎片,禁章节倾倒**。

## 4. merge + link/moc/compile(加载 kb-link)

merge 提案 → `ir/knowledge.json`(NEW/UPDATE/DUPLICATE/CONFLICT/UNCERTAIN);
link 互链;topics.json 主题聚合;编译笔记进 `staging/`。

## 5. qa → review → commit

```bash
powershell -File <本skill>/scripts/run.ps1 qa_check.py --state <dir>   # 必须通过
# review: 按 prompts/review.md 批量呈现,永远带"保持未知"选项
powershell -File <本skill>/scripts/run.ps1 commit.py --state <dir> commit
```

## 6. 增量更新(后续新材料)

同 2-5,只是:重复文件零变化;已存在概念复用稳定 id;
只有受影响笔记更新;用户手写内容(managed 区域外)保留。
回滚:`commit.py rollback <run_id>`;`commit.py list-runs` 列历史。

## 状态目录

```
<vault>/.learning-kb/            # 或 brief 指定的 --state
├── BRIEF.md / brief.json / status.json / sources.json / review.json
├── sources/<sha[:12]>.<ext>     # 原文件
├── extracted/<src_id>.md  assets/<src_id>/
├── ir/documents/  ir/proposals/  ir/knowledge.json  ir/topics.json
├── runs/<run_id>.json  runs/backups/<run_id>/
└── staging/
```

## 脚本运行约定

- 一律 `powershell -File scripts/run.ps1 <脚本> <参数>`;
- 首次运行自动 `setup.ps1`(uv 建 venv + 装依赖,含 whisper/torch,较慢);
- `--state` 必填,指向 `.learning-kb`;
- `--input`/`--url` 支持一次传多个,单项失败不中断批次(退出码 1 表示有失败);
- 脚本只做确定性转换,不做理解;理解全部走子 skill 协议。

## 测试

完整测试套件在 `tests/`(83 例:单元 + 转换器 + e2e 全管线 + 增量 +
压测体量/unicode/损坏文件):

```bash
uv pip install --python .venv/Scripts/python.exe -r scripts/requirements-dev.txt
.venv/Scripts/python.exe -m pytest tests
```

压测单独:`-m stress`;PowerShell 冒烟:`-m powershell`。

## 黄金规则

1. 永不修改原始材料;内容寻址去重。
2. 每条知识必带来源(源 + 块 + 定位),可追溯。
3. 视觉:不能看图就说不能,绝不假装看过;存疑进 review。
4. 粒度:条目"大而完整",笔记按主题聚合,一条目一笔记是错的。
5. 冲突:真矛盾双保留,绝不替用户选边;合并拿不准走 UNCERTAIN。
6. 外部知识永远显式标记(external + callout),档位尊重 brief。
7. review 批量处理、永远带"保持未知",管线不因单条卡死。
8. 先 qa 后 commit;每次 commit 有 manifest 与备份;崩溃可回滚。
9. 断点续行靠磁盘状态,不靠对话记忆。
10. 缺依赖/缺环境时,给出明确的一键安装指引,不要静默绕过。
