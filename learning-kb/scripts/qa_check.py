"""staging 校验:wikilink/资产/重名/来源引用。用法:
  run.ps1 qa_check.py --state <dir>
通过时 exit 0;有任何问题 exit 1 并输出报告。
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common

WIKI_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
ASSET_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def check(state_dir):
    state, sources, status = common.load_state(state_dir)
    staging = state / "staging"
    issues, n_notes, n_items = [], 0, 0

    # ---- staging 校验(存在时)----
    if staging.exists():
        notes = sorted(staging.rglob("*.md"))
        n_notes = len(notes)
        note_basenames = {}
        for n in notes:
            b = n.stem.lower()
            note_basenames.setdefault(b, []).append(n)
        for b, files in note_basenames.items():
            if len(files) > 1:
                issues.append(f"重名笔记 {b}: {[str(f.relative_to(staging)) for f in files]}")
        rel_notes = {n.relative_to(staging).as_posix().replace(".md", "") for n in notes}
        rel_notes |= {n.relative_to(staging).as_posix() for n in notes}
        # vault 侧已有笔记(增量时 wikilink 可能指向既有笔记)
        vault = state.parent
        for vn in vault.rglob("*.md"):
            if ".learning-kb" in vn.parts:
                continue
            rel_notes.add(vn.relative_to(vault).as_posix().replace(".md", ""))
            rel_notes.add(vn.relative_to(vault).as_posix())
        for n in notes:
            text = n.read_text(encoding="utf-8", errors="replace")
            for m in WIKI_RE.finditer(text):
                target = m.group(1).strip()
                if target not in rel_notes:
                    issues.append(f"悬空 wikilink: {n.relative_to(staging)} -> [[{target}]]")
            for m in ASSET_RE.finditer(text):
                target = m.group(1)
                if target.startswith(("http", "#")):
                    continue
                if not (staging / target).exists() and not (state / target).exists():
                    issues.append(f"悬空资产: {n.relative_to(staging)} -> {target}")

    # ---- knowledge IR 校验(独立于 staging)----
    kf = state / "ir" / "knowledge.json"
    ids = set()
    if kf.exists():
        k = common.read_json(kf)
        src_ids = {s["id"] for s in sources["sources"]}
        for item in k.get("items", []):
            if item.get("id") in ids:
                issues.append(f"knowledge.json 重复条目 id: {item['id']}")
            ids.add(item["id"])
            for src in item.get("sources", []):
                if src.get("src_id") not in src_ids:
                    issues.append(f"条目 {item.get('id')} 引用了未知来源 {src.get('src_id')}")
            ext = item.get("external")
            if ext and ext.get("trust") not in ("official", "high", "low"):
                issues.append(f"条目 {item.get('id')} external.trust 非法: {ext.get('trust')}")
        for item in k.get("items", []):
            for l in item.get("links", []):
                if l not in ids:
                    issues.append(f"条目 {item.get('id')} 悬空 links -> {l}")
        n_items = len(ids)
    return issues, n_notes, n_items


def main():
    p = common.base_argparser("QA 校验")
    args = p.parse_args()
    issues, n_notes, n_items = check(args.state)
    print(f"[qa] 笔记 {n_notes} 篇,知识条目 {n_items} 条,问题 {len(issues)} 个")
    for i in issues:
        print("  - " + i)
    if issues:
        report = Path(args.state) / "qa-report.json"
        common.write_json(report, {"issues": issues})
        print(f"[qa] 未通过,报告已写 {report}")
        sys.exit(1)
    print("[qa] 通过")


if __name__ == "__main__":
    main()
