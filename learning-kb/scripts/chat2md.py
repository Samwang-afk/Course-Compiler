"""聊天导出 / 表格数据 -> markdown。用法:
  run.ps1 chat2md.py --state <dir> --input a.txt --format auto|chat|table
    chat: 形如 "2023-01-01 12:00 张三" 开头的行解析为对话
    table: csv/tsv/json 列表 -> markdown 表格
"""
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common

CHAT_RE = re.compile(r"^(?P<ts>\d{2,4}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2}(:\d{2})?)\s+(?P<who>\S+)\s*[:：]?\s*(?P<body>.*)$")


def as_chat(text):
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = CHAT_RE.match(line)
        if m:
            out.append(f"<!-- time:{m.group('ts').split()[-1] if ' ' in m.group('ts') else m.group('ts')} -->")
            out.append(f"**{m.group('who')}**: {m.group('body')}")
        else:
            out.append(line)
    return out


def as_table(text, suffix):
    if suffix == ".json":
        data = json.loads(text)
        if isinstance(data, dict):
            data = [data]
        if not data or not isinstance(data, list):
            sys.exit("json 需为对象列表")
        keys = list(data[0].keys())
        rows = [[str(r.get(k, "")) for k in keys] for r in data]
    else:
        delim = "\t" if suffix == ".tsv" else ","
        rows = list(csv.reader(text.splitlines(), delimiter=delim))
        if not rows:
            return []
        keys = rows[0]
        rows = rows[1:]
    out = ["| " + " | ".join(str(k) for k in keys) + " |",
           "|" + "---|" * len(keys)]
    for r in rows:
        out.append("| " + " | ".join(c.replace("|", "\\|").replace("\n", " ") for c in r) + " |")
    return out


def convert_one(state_dir, path: Path, fmt):
    text = path.read_text(encoding="utf-8", errors="replace")
    if fmt == "auto":
        fmt = "chat" if CHAT_RE.search(text) else "table"
    kind = "chat" if fmt == "chat" else "table"
    entry, dup = common.register(state_dir, kind, path)
    if dup:
        print(f"[跳过] 内容重复,已有 {entry['id']} ({entry['title']})")
        return
    try:
        _convert(state_dir, path, entry, text, fmt)
    except Exception:
        common.remove_source(state_dir, entry["id"])
        raise


def _convert(state_dir, path, entry, text, fmt):
    state, _, _ = common.load_state(state_dir)
    body = as_chat(text) if fmt == "chat" else as_table(text, path.suffix.lower())
    out = [f"<!-- src:{entry['id']} title:{entry['title']} -->", ""] + body
    md = state / "extracted" / f"{entry['id']}.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text("\n".join(out), encoding="utf-8")
    common.update_source(state_dir, entry["id"],
                         extracted_file=f"extracted/{entry['id']}.md",
                         meta={"format": fmt}, status="extracted")
    print(f"[ok] {entry['id']} {path.name} (format={fmt})")


def main():
    p = common.base_argparser("聊天/表格 -> markdown")
    p.add_argument("--input", required=True, action="append", nargs="+", help="文件,可多个")
    p.add_argument("--format", default="auto", choices=["auto", "chat", "table"])
    args = p.parse_args()
    sys.exit(common.run_batch(common.flatten(args.input),
                              lambda f: convert_one(args.state, Path(f), args.format)))


if __name__ == "__main__":
    main()
