# SKILL: kb-ingest(收材料)

把各种格式的学习材料收进 `.learning-kb` 工作区,归一为 markdown + Document IR 入口。
由 `learning-kb` 主 skill 路由,也可独立使用。本 skill 不含理解:只做确定性转换。

共享件位于相对路径 `../learning-kb/`(scripts / schemas / templates)。
运行约定:`powershell -File ../learning-kb/scripts/run.ps1 <脚本> <参数>`,
首次运行会自动安装依赖(见 ../learning-kb/scripts/setup.ps1)。

## 流程

1. 确认 brief 已存在(`.learning-kb/brief.json`),没有则先回主 skill 做 brief。
2. 按格式选脚本,一次可投多个文件:
   - PDF → `pdf2md.py`
   - DOCX → `docx2md.py`
   - PPTX → `pptx2md.py`
   - EPUB → `epub2md.py`
   - Markdown/TXT → 直接登记后复制到 extracted(无专用脚本,用手工登记:见下)
   - 音频/视频 → `transcribe.py`(whisper,默认 base 模型,可 --model 调大)
   - 网页 → `fetch_url.py --url <url>`
   - 聊天/表格 → `chat2md.py --format auto|chat|table`
3. 每步检查输出:`[ok] src_xxxx` 或 `[跳过]`(重复)。
   报错的文件单独记录原因,继续其他文件,最后汇总。
4. 全部转 `parse_ir.py --all` → Document IR。
5. `status.json` stage → extract,把控制权交回主 skill。

## Markdown/TXT 手工登记

```
写 extracted/<src_id>.md,内容形如:
  <!-- src:src_0007 title:标题 -->
  正文…
在 sources.json 中按 schemas/source.schema.json 追加条目(status: parsed),
在 status.json 的 sources 中登记同状态。
```

## 失败处置

- 单文件失败不阻塞批次;把失败文件与原因列给用户,给两条路:
  重试 / 跳过该文件继续。
- 密码保护的 PDF、DRM 的 EPUB、损坏文件:明确报告,不猜测内容。
- 转写语言错误:重跑 `transcribe.py --force` 换模型,或让用户确认语言后
  由 extract 阶段注明。

## 图片资产

所有图片落 `assets/<src_id>/`,extracted markdown 用相对路径引用。
不删除、不改名原图。OCR 由 parse_ir 不负责;extract 阶段按视觉能力处理。
