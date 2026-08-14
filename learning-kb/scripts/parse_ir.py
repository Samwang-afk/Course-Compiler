"""markdown -> Document IR。用法:
  run.ps1 parse_ir.py --state <dir> [--src src_0001] [--all]
输出 ir/documents/<src_id>.json 并把源状态推进到 parsed。
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common

REF_RE = re.compile(r"^<!--\s*(page|slide|time|chapter)\s*:\s*(\S+)\s*-->$")
IMG_RE = re.compile(r"^!\[(.*?)\]\(([^)]+)\)\s*(<!--.*-->)?\s*$")
SRC_RE = re.compile(r"^<!--\s*src:(\S+)\s+title:(.*?)\s*-->$")


def parse_md(text):
    blocks, cur_ref, n = [], None, 0

    def add(t, **kw):
        nonlocal n
        n += 1
        kw.update({"id": f"b{n}", "type": t, "order": n})
        if cur_ref and "ref" not in kw:
            kw["ref"] = cur_ref
        blocks.append(kw)

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        m = REF_RE.match(line.strip())
        if m:
            cur_ref = f"{m.group(1)}:{m.group(2)}"
            i += 1
            continue
        m = IMG_RE.match(line.strip())
        if m:
            alt, target = m.group(1), m.group(2)
            kw = {"caption": alt, "asset": target}
            if m.group(3):
                rm = REF_RE.match(m.group(3).strip())
                if rm:
                    cur_ref = f"{rm.group(1)}:{rm.group(2)}"
                    kw["ref"] = cur_ref
            add("figure", **kw)
            i += 1
            continue
        if line.lstrip().startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            add("heading", level=level, text=line.lstrip("#").strip())
            i += 1
            continue
        if line.strip().startswith("```"):
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            add("code", text="\n".join(code))
            continue
        if line.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]):
            rows = []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(cells)
                i += 1
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            add("table", text=str({"header": header, "rows": rows}))
            continue
        if line.strip().startswith(">"):
            q = [line.lstrip("> ").strip()]
            i += 1
            while i < len(lines) and lines[i].strip().startswith(">"):
                q.append(lines[i].lstrip("> ").strip())
                i += 1
            add("quote", text="\n".join(q))
            continue
        if re.match(r"^\s*[-*+]\s+", line):
            items = [re.sub(r"^\s*[-*+]\s+", "", line)]
            i += 1
            while i < len(lines) and re.match(r"^\s*[-*+]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*+]\s+", "", lines[i]))
                i += 1
            add("list", text="\n".join(items))
            continue
        if re.match(r"^\s*\d+[.)]\s+", line):
            items = [re.sub(r"^\s*\d+[.)]\s+", "", line)]
            i += 1
            while i < len(lines) and re.match(r"^\s*\d+[.)]\s+", lines[i]):
                items.append(re.sub(r"^\s*\d+[.)]\s+", "", lines[i]))
                i += 1
            add("list", text="\n".join(items))
            continue
        if line.strip().startswith("$$") or re.search(r"^\s*\$[^$]+\$\s*$", line):
            eq = line.strip().strip("$").strip()
            add("equation", text=eq)
            i += 1
            continue
        if SRC_RE.match(line.strip()) or line.strip().startswith("<!--"):
            i += 1
            continue
        para = [line.strip()]
        i += 1
        while i < len(lines) and lines[i].strip() and not REF_RE.match(lines[i].strip()) \
                and not lines[i].lstrip().startswith(("#", "|", ">", "```")) \
                and not re.match(r"^\s*[-*+]\s+", lines[i]) \
                and not IMG_RE.match(lines[i].strip()):
            para.append(lines[i].strip())
            i += 1
        add("paragraph", text="\n".join(para))
    return blocks


def parse_one(state_dir, sid):
    state, sources, status = common.load_state(state_dir)
    src = next((s for s in sources["sources"] if s["id"] == sid), None)
    if not src:
        sys.exit(f"未知来源 {sid}")
    md_file = src.get("extracted_file")
    if not md_file or not (state / md_file).exists():
        sys.exit(f"{sid} 无 extracted 文件,先 ingest")
    text = (state / md_file).read_text(encoding="utf-8")
    m = SRC_RE.search(text)
    title = m.group(2).strip() if m else src["title"]
    ir = {"version": 1, "src_id": sid, "title": title, "blocks": parse_md(text)}
    out = state / "ir" / "documents" / f"{sid}.json"
    common.write_json(out, ir)
    common.update_source(state_dir, sid, status="parsed")
    print(f"[ok] {sid} {title}: {len(ir['blocks'])} 块 -> {out.name}")


def main():
    p = common.base_argparser("markdown -> Document IR")
    p.add_argument("--src", help="单个源 id")
    p.add_argument("--all", action="store_true", help="所有 extracted 状态但未 parsed 的源")
    args = p.parse_args()
    state, sources, _ = common.load_state(args.state)
    if args.src:
        parse_one(args.state, args.src)
    elif args.all:
        todo = [s["id"] for s in sources["sources"]
                if s["status"] in ("registered", "extracted") and s.get("extracted_file")]
        sys.exit(common.run_batch(todo, lambda sid: parse_one(args.state, sid), label="源"))
    else:
        p.print_help()


if __name__ == "__main__":
    main()
